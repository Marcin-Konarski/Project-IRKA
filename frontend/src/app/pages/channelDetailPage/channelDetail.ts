import { Component, DestroyRef, computed, effect, inject, signal } from "@angular/core";
import { ActivatedRoute, Router, RouterLink } from "@angular/router";
import { takeUntilDestroyed } from "@angular/core/rxjs-interop";
import { ApiService } from "../../core/http/apiService";
import { ChannelMessageData } from "../../types";
import { HighlightPipe } from "../../pipes/highlight.pipe";

function normalizeSearchQuery(value: string): string {
    return value.trim().toLowerCase();
}

@Component({
    standalone: true,
    selector: 'app-channel-detail',
    templateUrl: './channelDetail.html',
    imports: [RouterLink, HighlightPipe],
    host: {
        class: 'block w-full h-full min-h-0 overflow-y-auto',
    },
})
export class ChannelDetailPage {
    http = inject(ApiService);
    route = inject(ActivatedRoute);
    router = inject(Router);
    private destroyRef = inject(DestroyRef);

    channelId = signal<number | null>(null);
    channelName = signal("");
    channelTitle = signal("");
    allMessages = signal<ChannelMessageData[]>([]);
    searchQuery = signal("");
    currentPage = signal(1);
    readonly messagesPerPage = 10;
    favorites = signal<Set<string>>(new Set());
    favoriteIds = signal<Map<string, string>>(new Map());
    targetMessageId = signal<number | null>(null);

    constructor() {
        const id = Number(this.route.snapshot.paramMap.get("channelId"));
        const messageId = this.parsePageParam(this.route.snapshot.queryParamMap.get("messageId"));
        if (messageId > 0) {
            this.targetMessageId.set(messageId);
        }

        this.route.queryParamMap.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(params => {
            const page = this.parsePageParam(params.get("page"));
            if (page !== this.currentPage()) {
                this.currentPage.set(page);
            }
            const msgId = this.parsePageParam(params.get("messageId"));
            this.targetMessageId.set(msgId > 0 ? msgId : null);
        });

        effect(() => {
            const page = this.currentPage();
            const currentUrlPage = this.parsePageParam(this.route.snapshot.queryParamMap.get("page"));
            if (page === currentUrlPage) return;
            void this.router.navigate([], {
                relativeTo: this.route,
                queryParams: { page: page > 1 ? page : null },
                queryParamsHandling: "merge",
                replaceUrl: true,
            });
        });

        effect(() => {
            if (this.targetMessageId() && this.allMessages().length > 0) {
                this.scrollToTargetMessage();
            }
        });

        if (id) {
            this.channelId.set(id);
            void this.loadChannel();
            void this.loadFavorites();
        }
    }

    private parsePageParam(value: string | null): number {
        const parsed = Number(value);
        if (!Number.isInteger(parsed) || parsed < 1) return 1;
        return parsed;
    }

    async loadChannel() {
        const id = this.channelId();
        if (!id) return;

        const [channelsResp, messagesResp] = await Promise.all([
            this.http.getChannels(),
            this.http.getChannelMessages(id),
        ]);

        if (channelsResp.ok) {
            const channels = channelsResp.response.body ?? [];
            const channel = channels.find(c => c.id === id);
            if (channel) {
                this.channelName.set(channel.channel_name);
                this.channelTitle.set(channel.title ?? "");
            }
        }

        if (messagesResp.ok) {
            this.allMessages.set(messagesResp.response.body ?? []);
        }

        this.clampPage();
        this.scrollToTargetMessage();
    }

    private scrollToTargetMessage() {
        const msgId = this.targetMessageId();
        if (!msgId) return;

        const idx = this.allMessages().findIndex(m => m.message_id === msgId);
        if (idx < 0) return;

        const page = Math.floor(idx / this.messagesPerPage) + 1;
        this.currentPage.set(page);

        setTimeout(() => {
            const el = document.getElementById(`message-${msgId}`);
            el?.scrollIntoView({ behavior: "smooth", block: "center" });
        }, 100);
    }

    async loadFavorites() {
        const resp = await this.http.getFavorites();
        if (resp.ok) {
            const set = new Set<string>();
            const map = new Map<string, string>();
            for (const f of resp.response.body ?? []) {
                const key = `${f.channel_id}:${f.message_id}`;
                set.add(key);
                map.set(key, f.id);
            }
            this.favorites.set(set);
            this.favoriteIds.set(map);
        }
    }

    isFavorite(channelId: number, messageId: number): boolean {
        return this.favorites().has(`${channelId}:${messageId}`);
    }

    async toggleFavorite(channelId: number, messageId: number, channelName: string, text: string, mediaUrl: string | undefined, mediaType: string | undefined, telegramUrl: string | undefined, date: string | undefined) {
        const key = `${channelId}:${messageId}`;
        if (this.isFavorite(channelId, messageId)) {
            const id = this.favoriteIds().get(key);
            if (id) {
                const resp = await this.http.removeFavorite(id);
                if (resp.ok) {
                    const next = new Set(this.favorites());
                    next.delete(key);
                    this.favorites.set(next);
                    const nextIds = new Map(this.favoriteIds());
                    nextIds.delete(key);
                    this.favoriteIds.set(nextIds);
                }
            }
        } else {
            const resp = await this.http.addFavorite({
                channel_id: channelId,
                message_id: messageId,
                channel_name: channelName,
                text,
                media_url: mediaUrl ?? null,
                media_type: mediaType ?? null,
                telegram_url: telegramUrl ?? null,
                date: date ?? null,
            });
            if (resp.ok) {
                const next = new Set(this.favorites());
                next.add(key);
                this.favorites.set(next);
                const nextIds = new Map(this.favoriteIds());
                nextIds.set(key, resp.response.body!.id);
                this.favoriteIds.set(nextIds);
            }
        }
    }

    formatDate(date: string): string {
        return date ? new Date(date).toLocaleString() : "";
    }

    private clampPage() {
        const maxPage = this.totalPages();
        if (this.currentPage() > maxPage) {
            this.currentPage.set(maxPage);
        }
    }

    filteredMessages = computed(() => {
        const query = normalizeSearchQuery(this.searchQuery());
        if (!query) {
            return this.allMessages();
        }
        return this.allMessages().filter(message => {
            const text = message.text?.trim().toLowerCase() || "";
            return text.includes(query);
        });
    });

    totalPages = computed(() => {
        const total = this.filteredMessages().length;
        return Math.max(1, Math.ceil(total / this.messagesPerPage));
    });

    paginatedMessages = computed(() => {
        const page = this.currentPage();
        const start = (page - 1) * this.messagesPerPage;
        return this.filteredMessages().slice(start, start + this.messagesPerPage);
    });

    onSearchInput(value: string) {
        this.searchQuery.set(value);
        this.currentPage.set(1);
        this.clampPage();
    }

    goToPreviousPage() {
        this.currentPage.update(value => Math.max(1, value - 1));
    }

    goToNextPage() {
        this.currentPage.update(value => Math.min(this.totalPages(), value + 1));
    }
}
