import { Component, DestroyRef, computed, effect, inject, signal } from "@angular/core";

import { Card } from "../../components/card/card";
import { ApiService } from "../../core/http/apiService";
import { streamService } from "../../core/http/streamService";
import { takeWhile, tap } from "rxjs";
import { takeUntilDestroyed } from "@angular/core/rxjs-interop";
import { ActivatedRoute, Router } from "@angular/router";
import { Modal } from "../../components/modal/modal";
import { JobStatusStreamData, ChannelCardData, ChannelMessageData } from "../../types";
type ObservedChannel = {
    channelName: string;
    status: string;
    ts: number; // timestamp for sorting (ms since epoch)
    id?: number;
    title?: string;
};

type SearchMessage = {
    key: string;
    channelName: string;
    channelTitle: string;
    text: string;
    mediaUrl?: string;
    mediaType?: string;
    dateLabel: string;
    ts: number;
    searchIndex: string;
};

type GroupedSearchResult = {
    channelKey: string;
    channelName: string;
    channelTitle: string;
    latestTs: number;
    messages: SearchMessage[];
};

function normalizeChannelName(channelName: string): string {
    const value = channelName.trim();

    if (value.startsWith("http://") || value.startsWith("https://")) {
        try {
            const parsed = new URL(value);
            if (parsed.hostname.endsWith("t.me")) {
                return parsed.pathname.replace(/^\/+/, "").trim();
            }
        } catch {
            // Fall through to the generic normalization below.
        }
    }

    if (value.includes("t.me/")) {
        return value.split("t.me/", 2)[1].replace(/^\/+/, "").trim();
    }

    return value.replace(/^@/, "").replace(/^\/+|\/+$/g, "").trim();
}

function channelKey(channelName: string): string {
    return normalizeChannelName(channelName).toLowerCase();
}

function normalizeSearchQuery(value: string): string {
    return value.trim().toLowerCase();
}


@Component({
    standalone: true,
    selector: 'app-channels',
    templateUrl: './channels.html',
    imports: [Card, Modal],
    host: {
        class: 'block w-full h-full min-h-0',
    },
})
export class ChannelsPage {
    http = inject(ApiService);
    stream = inject(streamService);
    route = inject(ActivatedRoute);
    router = inject(Router);
    private destroyRef = inject(DestroyRef);
    observedChannels = signal<ObservedChannel[]>([]);
    deletingChannelId = signal<number | null>(null);
    searchQuery = signal("");
    currentPage = signal(1);
    readonly pageSize = 10;
    visibleMessages = signal<SearchMessage[]>([]);
    filteredMessages = computed(() => {
        const query = normalizeSearchQuery(this.searchQuery());

        if (!query) {
            return [];
        }

        return this.visibleMessages().filter(message => message.searchIndex.includes(query));
    });
    groupedFilteredMessages = computed(() => {
        const grouped = new Map<string, GroupedSearchResult>();

        for (const message of this.filteredMessages()) {
            const key = channelKey(message.channelName);
            const current = grouped.get(key);

            if (!current) {
                grouped.set(key, {
                    channelKey: key,
                    channelName: message.channelName,
                    channelTitle: message.channelTitle,
                    latestTs: message.ts,
                    messages: [message],
                });
                continue;
            }

            current.messages.push(message);
            if (message.ts > current.latestTs) {
                current.latestTs = message.ts;
            }
        }

        return [...grouped.values()]
            .map(group => ({
                ...group,
                messages: group.messages.sort((a, b) => b.ts - a.ts),
            }))
            .sort((a, b) => b.latestTs - a.latestTs);
    });
    totalPages = computed(() => {
        const total = this.groupedFilteredMessages().length;
        return Math.max(1, Math.ceil(total / this.pageSize));
    });
    paginatedChannelResults = computed(() => {
        const page = this.currentPage();
        const start = (page - 1) * this.pageSize;
        return this.groupedFilteredMessages().slice(start, start + this.pageSize);
    });
    // Modal related stuff:
    modalHeader = signal("Add new channel");
    modalLabel = signal("channel name");

    constructor() {
        this.route.queryParamMap
            .pipe(takeUntilDestroyed(this.destroyRef))
            .subscribe(params => {
                const query = params.get("q") ?? "";
                const page = this.parsePageParam(params.get("page"));

                if (query !== this.searchQuery()) {
                    this.searchQuery.set(query);
                }

                if (page !== this.currentPage()) {
                    this.currentPage.set(page);
                }
            });

        effect(() => {
            const page = this.currentPage();
            const maxPage = this.totalPages();
            if (page > maxPage) {
                this.currentPage.set(maxPage);
            }
            if (page < 1) {
                this.currentPage.set(1);
            }
        });

        effect(() => {
            const query = this.searchQuery().trim();
            const page = this.currentPage();

            const currentUrlQuery = this.route.snapshot.queryParamMap.get("q") ?? "";
            const currentUrlPage = this.parsePageParam(this.route.snapshot.queryParamMap.get("page"));

            if (query === currentUrlQuery && page === currentUrlPage) {
                return;
            }

            void this.router.navigate([], {
                relativeTo: this.route,
                queryParams: {
                    q: query || null,
                    page: page > 1 ? page : null,
                },
                queryParamsHandling: "merge",
                replaceUrl: true,
            });
        });

        void this.loadObservedChannels();
    }

    private parsePageParam(value: string | null): number {
        const parsed = Number(value);
        if (!Number.isInteger(parsed) || parsed < 1) {
            return 1;
        }
        return parsed;
    }

    onSearchInput(value: string) {
        this.searchQuery.set(value);
        this.currentPage.set(1);
    }

    goToPreviousPage() {
        this.currentPage.update(value => Math.max(1, value - 1));
    }

    goToNextPage() {
        this.currentPage.update(value => Math.min(this.totalPages(), value + 1));
    }

    async loadObservedChannels() {
        const [channelsResp, jobsResp] = await Promise.all([this.http.getChannels(), this.http.getBackfillJobs()]);

        console.log("channelsResp:", channelsResp);
        console.log("jobsResp:", jobsResp);

        const channels: ChannelCardData[] = channelsResp.ok ? (channelsResp.response.body ?? []) : [];
        if (!channelsResp.ok) console.error("Failed to load channels:", channelsResp.error);

        const jobs: any[] = jobsResp.ok ? (jobsResp.response.body ?? []) : [];
        if (!jobsResp.ok) console.error("Failed to load backfill jobs:", jobsResp.error);

        // Build quick lookup for current in-memory entries to preserve their status
        const currentMap = new Map<string, ObservedChannel>();
        for (const c of this.observedChannels()) {
            currentMap.set(channelKey(c.channelName), c);
        }

        const mergedMap = new Map<string, ObservedChannel>();

        // Recent jobs (include done) - keep newest first (by created_at)
        for (const job of jobs) {
            const normalizedName = normalizeChannelName(job.channel_name);
            const key = channelKey(job.channel_name);
            const current = currentMap.get(key);
            mergedMap.set(key, current ?? {
                channelName: normalizedName,
                status: job.progress_count ? `${job.progress_count} messages` : job.status,
                ts: job.created_at ? new Date(job.created_at).getTime() : Date.now(),
            });
        }

        for (const ch of channels) {
            const key = channelKey(ch.channel_name);
            const current = currentMap.get(key) ?? mergedMap.get(key);

            if (current) {
                mergedMap.set(key, {
                    ...current,
                    id: ch.id,
                    title: ch.title,
                });
                continue;
            }

            mergedMap.set(key, {
                channelName: normalizeChannelName(ch.channel_name),
                status: ch.message_count > 0 ? `${ch.message_count} messages` : 'observed',
                ts: ch.created_at ? new Date(ch.created_at).getTime() : 0,
                id: ch.id,
                title: ch.title,
            });
        }

        const visibleChannels = [...mergedMap.values()].sort((a, b) => b.ts - a.ts).slice(0, 10);
        this.observedChannels.set(visibleChannels);

        await this.loadVisibleMessages(visibleChannels);
    }

    async loadVisibleMessages(channels: ObservedChannel[]) {
        const channelsWithIds = channels.filter((channel): channel is ObservedChannel & { id: number } => typeof channel.id === "number");

        if (channelsWithIds.length === 0) {
            this.visibleMessages.set([]);
            return;
        }

        const messageResults = await Promise.all(
            channelsWithIds.map(async channel => {
                const response = await this.http.getChannelMessages(channel.id);

                if (!response.ok) {
                    console.error(`Failed to load messages for channel ${channel.channelName}:`, response.error);
                    return [];
                }

                const messages: ChannelMessageData[] = response.response.body ?? [];

                return messages.map(message => {
                    const text = message.text?.trim() || "No text available";
                    const dateLabel = message.date ? new Date(message.date).toLocaleString() : "";
                    const channelTitle = channel.title?.trim() || channel.channelName;
                    const searchIndex = normalizeSearchQuery(text);

                    return {
                        key: `${channel.id}:${message.message_id}`,
                        channelName: channel.channelName,
                        channelTitle,
                        text,
                        mediaUrl: message.media_url ?? undefined,
                        mediaType: message.media_type ?? undefined,
                        dateLabel,
                        ts: message.date ? new Date(message.date).getTime() : 0,
                        searchIndex,
                    };
                });
            })
        );

        this.visibleMessages.set(
            messageResults.flat().sort((a, b) => b.ts - a.ts)
        );
    }

    private upsertObservedChannel(channelName: string, status: string) {
        const now = Date.now();
        const normalizedChannelName = normalizeChannelName(channelName);
        const key = channelKey(channelName);
        this.observedChannels.update(current => {
            const next = current.filter(channel => channelKey(channel.channelName) !== key);
            return [{ channelName: normalizedChannelName, status, ts: now }, ...next].sort((a,b) => b.ts - a.ts).slice(0, 10);
        });
    }


    async addChannel(channelName: string) {
        const normalizedChannelName = normalizeChannelName(channelName);
        if (!normalizedChannelName) {
            return;
        }

        console.log("Starting backfill for channel:", normalizedChannelName);

        const response = await this.http.startBackfill({"channel": normalizedChannelName});

        if (!response.ok) {
            console.error("Backfill request failed:", response.error);
            this.upsertObservedChannel(normalizedChannelName, 'failed');
            return;
        }

        const jobId = response.response.body!.job_id;
        console.log("Backfill job created:", jobId);
        this.upsertObservedChannel(normalizedChannelName, 'queued');

        this.stream.streamJobStatus(jobId).pipe(
            tap((value: JobStatusStreamData) => {
                console.log("Backfill progress:", normalizedChannelName, value);
                this.upsertObservedChannel(normalizedChannelName, value.status);

                if (value.status === "done") {
                    void this.loadObservedChannels();
                }
            }),
            takeWhile((value: JobStatusStreamData) => value.status !== "done" && value.status !== 'failed', true),
            takeUntilDestroyed(this.destroyRef),
        ).subscribe({
            error: error => {
                console.error("SSE subscription failed:", error);
                this.upsertObservedChannel(normalizedChannelName, 'failed');
            },
            complete: () => {
                console.log("Backfill stream completed:", normalizedChannelName);
                this.upsertObservedChannel(normalizedChannelName, 'done');
            },
        });
    }

    async deleteChannel(channel: ObservedChannel) {
        if (typeof channel.id !== "number") {
            return;
        }

        this.deletingChannelId.set(channel.id);

        const response = await this.http.deleteChannel(channel.id);
        if (!response.ok) {
            console.error(`Failed to delete channel ${channel.channelName}:`, response.error);
            this.deletingChannelId.set(null);
            return;
        }

        this.observedChannels.update(current =>
            current.filter(item => item.id !== channel.id)
        );

        this.visibleMessages.update(current =>
            current.filter(message => message.channelName !== channel.channelName)
        );

        this.deletingChannelId.set(null);
        await this.loadObservedChannels();
    }


}