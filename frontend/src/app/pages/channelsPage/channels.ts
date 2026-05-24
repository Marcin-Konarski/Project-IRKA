import { Component, DestroyRef, computed, inject, signal } from "@angular/core";

import { Card } from "../../components/card/card";
import { ApiService } from "../../core/http/apiService";
import { streamService } from "../../core/http/streamService";
import { takeWhile, tap } from "rxjs";
import { takeUntilDestroyed } from "@angular/core/rxjs-interop";
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
    dateLabel: string;
    ts: number;
    searchIndex: string;
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
    private destroyRef = inject(DestroyRef);
    observedChannels = signal<ObservedChannel[]>([]);
    searchQuery = signal("");
    visibleMessages = signal<SearchMessage[]>([]);
    filteredMessages = computed(() => {
        const query = normalizeSearchQuery(this.searchQuery());

        if (!query) {
            return [];
        }

        return this.visibleMessages().filter(message => message.searchIndex.includes(query));
    });
    // Modal related stuff:
    modalHeader = signal("Add new channel");
    modalLabel = signal("channel name");

    constructor() {
        void this.loadObservedChannels();
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
                    const searchIndex = normalizeSearchQuery([channel.channelName, channelTitle, text].join(" "));

                    return {
                        key: `${channel.id}:${message.message_id}`,
                        channelName: channel.channelName,
                        channelTitle,
                        text,
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


}