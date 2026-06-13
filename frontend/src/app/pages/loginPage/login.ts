import { Component, inject, signal } from "@angular/core";
import { ActivatedRoute, Router } from "@angular/router";
import { form, FormField, FormRoot } from "@angular/forms/signals";

import { Alert } from "../../components/alert/alert";
import { ErrorAlert, LoginData } from "../../types";
import { ApiService } from "../../core/http/apiService";
import { UserState } from "../../core/state/userState";

@Component({
    standalone: true,
    selector: 'app-login',
    templateUrl: './login.html',
    imports: [FormField, FormRoot, Alert],
    host: {
        class: 'flex items-center justify-center min-h-[calc(100vh-64px)]'
    }
})
export class LoginPage {
    private route = inject(ActivatedRoute);
    private router = inject(Router);
    api = inject(ApiService);
    state = inject(UserState);
    showAlert = signal(false);
    showAuthRequiredAlert = signal(false);
    showSessionExpiredAlert = signal(false);
    showErrorAlert = signal<ErrorAlert>({errors: false, message: ''});
    private redirectTo = '/channels';

    constructor() {
        this.route.queryParams.subscribe((params) => {
            this.showAlert.set(params['showAlert'] === 'true');
            this.showAuthRequiredAlert.set(params['authRequired'] === 'true');
            this.showSessionExpiredAlert.set(params['sessionExpired'] === 'true');
            const redirectValue = typeof params['redirectTo'] === 'string' ? params['redirectTo'] : '';
            this.redirectTo = redirectValue.startsWith('/') ? redirectValue : '/channels';
        });
    };


    loginFormData = {
        username: '',
        password: '',
    }
    loginModel = signal<LoginData>(this.loginFormData);

    async onSubmit() {
        const formData = this.loginModel();
        this.showAlert.set(false);
        this.showAuthRequiredAlert.set(false);
        this.showSessionExpiredAlert.set(false);
        this.showErrorAlert.set({ errors: false, message: "" });

        const response = await this.api.login(formData);
        if (response?.ok) {
            const token = response.response.body?.access_token;
            if (!token) {
                this.showErrorAlert.set({ errors: true, message: "Login succeeded but no access token returned." });
                return;
            }

            this.state.setUser(formData.username, token); // TODO: make backend return here username in body as well and get username from response instead of formData
            this.loginForm().reset(this.loginFormData);
            this.router.navigateByUrl(this.redirectTo);
        } else {
            const error = response?.error;
            const status = error?.status;
            const detail = (error?.error as any)?.detail;

            this.showErrorAlert.set({ errors: true, message: "Invalid username or password." });
        }
    }

    loginForm = form(
        this.loginModel,
        {
            submission: {
                action: async () => this.onSubmit()
            }
        }
    )

}