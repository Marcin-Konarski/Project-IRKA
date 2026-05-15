import { Injectable, signal } from "@angular/core";


@Injectable({providedIn: "root"})
export class UserState {
    private readonly _isLoggedIn = signal(false);
    private readonly _username = signal("");
    private readonly _accessToken = signal("");

    readonly isLoggedIn = this._isLoggedIn.asReadonly();
    readonly username = this._username.asReadonly();
    readonly accessToken = this._accessToken.asReadonly();

    setUser(username: string, token: string) {
        this._isLoggedIn.set(true);
        this._username.set(username);
        this._accessToken.set(token);
    }

    clearUser() {
        this._isLoggedIn.set(false);
        this._username.set("");
        this._accessToken.set("");
    }

    setToken(value: string) {
        this._accessToken.set(value);
    }
}