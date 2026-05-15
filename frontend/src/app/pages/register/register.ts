import { Component, inject, signal } from "@angular/core";
import { Router } from "@angular/router";
import { email, form, FormField, FormRoot, minLength, required, SchemaPathTree, validate } from '@angular/forms/signals';

import { ErrorAlert, RegisterData } from "../../types";
import { ApiService } from "../../core/http/apiService";
import { Alert } from "../../components/alert/alert";


@Component({
    selector: 'app-register',
    templateUrl: './register.html',
    imports: [FormField, FormRoot, Alert],
    host: {
        class: 'flex items-center justify-center min-h-[calc(100vh-64px)]'
    }
})
export class RegisterPage {
    private router = inject(Router);
    api = inject(ApiService);
    showErrors = signal(false);
    showErrorAlert = signal<ErrorAlert>({errors: false, message: ''});

    registerFormData = {
        username: '',
        email: '',
        password: '',
        repeatPassword: '',
    }
    registerModel = signal<RegisterData>(this.registerFormData);

    private registerSchema(path: SchemaPathTree<RegisterData>) {
        required(path.username, {message: "Username is required"});
        minLength(path.username, 4, {message: "Username must be at least 4 characters"});

        required(path.email, {message: "Email is required"});
        email(path.email, {message: "Enter a valid email address"});

        required(path.password, {message: "Password is required"});
        minLength(path.password, 8, {message: "Password must be at least 8 characters"});

        required(path.repeatPassword, {message: "Repeat password is required"});
        validate(path.repeatPassword, ({ value, valueOf }) => {
            if (value() !== valueOf(path.password)) {
                return {
                    kind: "passwordMismatch",
                    message: "Passwords do not match",
                };
            }
            return null;
        });
    }


    async onSubmit() {
        const formData = this.registerModel();
        this.showErrorAlert.set({errors: false, message: ''});

        const response = await this.api.register(formData);
        if (response?.ok) {
            this.registerForm().reset(this.registerFormData);
            this.showErrors.set(false);

            this.router.navigate(['/login'], { queryParams: {
                showAlert: true, // TODO: change this to `success` variable instead of hardcoded `true`!!!
            } });
        } else {
            const error = response?.error;
            const detail = (error?.error as any)?.detail;
            this.showErrorAlert.set({
                errors: true,
                message: typeof detail === "string" ? detail : (error?.message ?? "Error During Signup"),
            });
        };
    }


    registerForm = form(
        this.registerModel,
        this.registerSchema,
        {
            submission: {
                action: async () => this.onSubmit()
            }
        }
    );

}