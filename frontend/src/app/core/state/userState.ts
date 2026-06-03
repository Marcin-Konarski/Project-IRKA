import { Injectable, signal } from "@angular/core";

import { isTokenExpired } from "../auth/token";


@Injectable({providedIn: "root"})
export class UserState {
    private static readonly TOKEN_KEY = "irka_access_token";
    private static readonly USERNAME_KEY = "irka_username";

    private readonly _isLoggedIn = signal(false);
    private readonly _username = signal("");
    private readonly _accessToken = signal("");

    readonly isLoggedIn = this._isLoggedIn.asReadonly();
    readonly username = this._username.asReadonly();
    readonly accessToken = this._accessToken.asReadonly();

    constructor() {
        const token = localStorage.getItem(UserState.TOKEN_KEY) ?? "";
        const username = localStorage.getItem(UserState.USERNAME_KEY) ?? "";

        if (token && !isTokenExpired(token)) {
            this._isLoggedIn.set(true);
            this._accessToken.set(token);
            this._username.set(username);
            return;
        }

        if (token) {
            this.clearUser();
        }
    }

    hasValidSession(): boolean {
        const token = this._accessToken();
        return Boolean(token) && !isTokenExpired(token);
    }

    setUser(username: string, token: string) {
        this._isLoggedIn.set(true);
        this._username.set(username);
        this._accessToken.set(token);

        localStorage.setItem(UserState.TOKEN_KEY, token);
        localStorage.setItem(UserState.USERNAME_KEY, username);
    }

    clearUser() {
        this._isLoggedIn.set(false);
        this._username.set("");
        this._accessToken.set("");

        localStorage.removeItem(UserState.TOKEN_KEY);
        localStorage.removeItem(UserState.USERNAME_KEY);
    }

    setToken(value: string) {
        this._accessToken.set(value);
        if (value) {
            localStorage.setItem(UserState.TOKEN_KEY, value);
            return;
        }

        localStorage.removeItem(UserState.TOKEN_KEY);
    }
}