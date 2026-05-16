import { HttpClient, HttpErrorResponse } from "@angular/common/http";
import { inject, Injectable } from "@angular/core";
import { firstValueFrom } from "rxjs";

import { ApiResult, LoginData, LoginResponseBody, RegisterData, RegisterResponseBody,
        StartBackfillReturnData, BackfillRequest } from "../../types";

export interface TelegramCodeRequest {
    phone: string;
}

export interface TelegramCodeResponse {
    phone_code_hash: string;
    message: string;
}

export interface TelegramVerifyRequest {
    phone: string;
    code: string;
    phone_code_hash: string;
}

@Injectable({providedIn: 'root'})
export class ApiService {
    private http = inject(HttpClient);
    private baseURL = 'http://localhost:8000'

    private async apiPostTemplate<TReq, TRes>(path: string, body: TReq | null = null): Promise<ApiResult<TRes>> {
        const url = `${this.baseURL}${path}`;

        try {
            const response = await firstValueFrom(
                this.http.post<TRes>(url, body, { observe: "response", timeout: 5000 })
            );
            console.log("logging 1:\n", response)
            return { ok: true, response };
        } catch (e) {
            const error = e as HttpErrorResponse;
            console.log("logging 2:\n", url, error.status, error.error ?? error.message);
            return { ok: false, error };
        }
    };

    async register(body: RegisterData) {
        return await this.apiPostTemplate<RegisterData, RegisterResponseBody>("/auth/signup", body);
    }

    async login(body: LoginData) {
        return await this.apiPostTemplate<LoginData, LoginResponseBody>("/auth/login", body);
    }

    async startBackfill(body: BackfillRequest) {
        return await this.apiPostTemplate<BackfillRequest, StartBackfillReturnData>("/backfill-jobs", body);
    }

    async requestTelegramCode(phone: string) {
        return await this.apiPostTemplate<TelegramCodeRequest, TelegramCodeResponse>(
            "/auth/telegram/request",
            { phone }
        );
    }

    async verifyTelegramCode(phone: string, code: string, phone_code_hash: string) {
        return await this.apiPostTemplate<TelegramVerifyRequest, any>(
            "/auth/telegram/verify",
            { phone, code, phone_code_hash }
        );
    }

}