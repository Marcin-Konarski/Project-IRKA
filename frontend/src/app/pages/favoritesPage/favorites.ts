import { Component, inject, signal } from "@angular/core";
import { RouterLink } from "@angular/router";
import { ApiService } from "../../core/http/apiService";
import { FavoriteMessageData } from "../../types";

@Component({
    standalone: true,
    selector: 'app-favorites',
    templateUrl: './favorites.html',
    imports: [RouterLink],
    host: {
        class: 'block w-full h-full min-h-0 overflow-y-auto',
    },
})
export class FavoritesPage {
    private api = inject(ApiService);

    favorites = signal<FavoriteMessageData[]>([]);
    isLoading = signal(true);
    errorMessage = signal("");

    constructor() {
        void this.loadFavorites();
    }

    async loadFavorites() {
        this.isLoading.set(true);
        this.errorMessage.set("");

        const resp = await this.api.getFavorites();
        if (resp.ok) {
            this.favorites.set(resp.response.body ?? []);
        } else {
            this.errorMessage.set("Failed to load favorites.");
        }
        this.isLoading.set(false);
    }

    async removeFavorite(id: string) {
        const resp = await this.api.removeFavorite(id);
        if (resp.ok) {
            this.favorites.update(list => list.filter(f => f.id !== id));
        }
    }

    formatDate(date: string | null | undefined): string {
        return date ? new Date(date).toLocaleString() : "";
    }
}
