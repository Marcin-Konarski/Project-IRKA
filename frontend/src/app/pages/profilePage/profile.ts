import { Component, inject, signal } from "@angular/core";

import { ApiService } from "../../core/http/apiService";
import { ProfileStatsData } from "../../types";

@Component({
    standalone: true,
    selector: 'app-profile',
    templateUrl: './profile.html',
    host: {
        class: 'block w-full h-full min-h-0',
    },
})
export class ProfilePage {
    private api = inject(ApiService);

    isLoading = signal(true);
    errorMessage = signal('');
    stats = signal<ProfileStatsData>({
        channels_count: 0,
        channels_sorted_by_messages: [],
    });

    constructor() {
        void this.loadProfileStats();
    }

    async loadProfileStats() {
        this.isLoading.set(true);
        this.errorMessage.set('');

        const response = await this.api.getProfileStats();

        if (!response.ok) {
            const detail = (response.error.error as any)?.detail;
            this.errorMessage.set(typeof detail === 'string' ? detail : 'Failed to load profile statistics.');
            this.isLoading.set(false);
            return;
        }

        this.stats.set(response.response.body ?? { channels_count: 0, channels_sorted_by_messages: [] });
        this.isLoading.set(false);
    }
}
