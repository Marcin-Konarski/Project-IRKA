import { Component, input, output } from "@angular/core";



@Component({
    standalone: true,
    selector: 'app-card',
    templateUrl: './card.html',
})
export class Card {
    channelName = input.required<string>();
    status = input<string>('Observed');
    channelId = input<number | undefined>(undefined);
    deleting = input<boolean>(false);
    deleteRequested = output<void>();

}