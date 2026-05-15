import { Component, inject, signal } from "@angular/core";
import { RouterLink } from "@angular/router";

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
    username = this.state.username;
    isLoggedIn = this.state.isLoggedIn;

    mainButtonText = signal('IRKA');

    dropdownButtonsList: NavButtons[] = [
        {
            id: 1,
            name: "Home",
            url: "/home"
        },
        {
            id: 2,
            name: "Channels",
            url: "/channels"
        },
        {
            id: 3,
            name: "Bomba",
            url: "/bomba"
        },
    ];


}