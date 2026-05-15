import { Component, inject, signal } from "@angular/core";
import { Alert } from "../../components/alert/alert";
import { ActivatedRoute } from "@angular/router";


@Component({
    standalone: true,
    selector: 'app-home',
    templateUrl: './home.html',
    imports: [Alert],
})
export class HomePage {
    route = inject(ActivatedRoute); 
    showLoginAlert = signal(false);


    constructor() {
        this.route.queryParams.subscribe((params) => {
            this.showLoginAlert.set(params['showLoginAlert'] === 'true');
        });
    };
    
}