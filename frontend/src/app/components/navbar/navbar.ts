import { Component, computed, inject, signal } from "@angular/core";
import { Router, RouterLink } from "@angular/router";

import { NavButtons } from "../../types";
import { UserState } from "../../core/state/userState";


@Component({
    selector: 'app-navbar',
    standalone: true,
    templateUrl: './navbar.html',
    imports: [RouterLink],
})
export class Navbar {
    state = inject(UserState);
    private router = inject(Router);
    username = this.state.username;
    isLoggedIn = this.state.isLoggedIn;
    showUsername = computed(() => this.isLoggedIn() && this.username().trim().length > 0);

    mainButtonText = signal('IRKA');

    dropdownButtonsList: NavButtons[] = [
        {
            id: 1,
            name: "Channels",
            url: "/channels"
        },
        {
            id: 2,
            name: "Telegram",
            url: "/telegram"
        },
    ];

    logout() {
        this.state.clearUser();
        void this.router.navigate(['/login']);
    }


}