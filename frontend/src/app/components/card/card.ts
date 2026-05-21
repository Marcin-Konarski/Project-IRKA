import { Component, input } from "@angular/core";



@Component({
    standalone: true,
    selector: 'app-card',
    templateUrl: './card.html',
})
export class Card {
    channelName = input.required<string>();
    status = input<string>('Observed');

}