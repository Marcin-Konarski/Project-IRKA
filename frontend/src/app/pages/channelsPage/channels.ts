import { Component, DestroyRef, inject, signal } from "@angular/core";
import { LucidePlus, LucideSearch } from '@lucide/angular';

import { Card } from "../../components/card/card";
import { ApiService } from "../../core/http/apiService";
import { streamService } from "../../core/http/streamService";
import { takeWhile, tap } from "rxjs";
import { takeUntilDestroyed } from "@angular/core/rxjs-interop";
import { Modal } from "../../components/modal/modal";


@Component({
    standalone: true,
    selector: 'app-channels',
    templateUrl: './channels.html',
    imports: [Card, Modal, LucidePlus, LucideSearch],
    host: {
        class: 'block w-full h-full min-h-0',
    },
})
export class ChannelsPage {
    http = inject(ApiService);
    stream = inject(streamService);
    private destroyRef = inject(DestroyRef);
    // Modal related stuff:
    modalHeader = signal("Add new channel");
    modalLabel = signal("channel name");


    async addChannel(channelName: string) {
        console.log(channelName);
        const response = await this.http.startBackfill({"channel": channelName}); // "nnm05716english"
        console.log("logging 3:\n", response);

        if (!response.ok) {
            console.log(response.error);
            return;
        }

        const jobId = response.response.body!.job_id;
        console.log("logging 4:\n", jobId);
        this.stream.streamJobStatus(jobId).pipe(
            tap(value => console.log("job queue:", value)),
            takeWhile(value => value.status !== "done" && value.status !== 'failed', true),
            takeUntilDestroyed(this.destroyRef),
        ).subscribe({
            error: error => console.error("SSE error", error),
            complete: () => console.log("SSE complete"),
        });
    }


}