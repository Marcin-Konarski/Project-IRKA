import { Component, input, output } from "@angular/core";
import { RouterLink } from "@angular/router";



@Component({
    standalone: true,
    selector: 'app-card',
    templateUrl: './card.html',
    imports: [RouterLink],
})
export class Card {
    channelName = input.required<string>();
    status = input<string>('Observed');
    channelId = input<number | undefined>(undefined);
    deleting = input<boolean>(false);
    deleteRequested = output<void>();
}