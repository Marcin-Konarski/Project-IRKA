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
    showErrorAlert = signal<ErrorAlert>({errors: false, message: ''});

    constructor() {
        this.route.queryParams.subscribe((params) => {
            this.showAlert.set(params['showAlert'] === 'true');
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
            this.router.navigate(['/'], { queryParams: { showLoginAlert: true } });
        } else {
            const error = response?.error;
            const detail = (error?.error as any)?.detail;

            this.showErrorAlert.set({
                errors: true,
                message: typeof detail === "string" ? detail : (error?.message ?? "Error during login"),
            });
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