import { Component, input, signal, effect } from "@angular/core";
import { LucideCircleX } from "@lucide/angular";

@Component({
    selector: 'app-alert',
    templateUrl: './alert.html',
    imports: [LucideCircleX],
})
export class Alert {
    type = input.required<string>();
    width = input<string>('w-96');
    visible = signal(true);
    // Message content of the alert should be in between tags for ng-content to pick it up

    constructor() {
        effect(() => {
            setTimeout(() => this.visible.set(false), 8000);
        });
    }

    close() {
        this.visible.set(false);
    }
}