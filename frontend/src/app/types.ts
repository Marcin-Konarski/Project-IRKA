import { HttpErrorResponse, HttpResponse } from "@angular/common/http";

export interface NavButtons {
    id: number;
    name: string;
    url: string;
    tag?: string;
}

export interface RegisterData {
    username: string;
    email: string;
    password: string;
    repeatPassword: string;
}

export interface RegisterResponseBody {
    id: string;
    username: string;
}

export interface LoginData {
    username: string;
    password: string;
}

export interface LoginResponseBody {
    access_token: string;
    token_type: string;
}

export type ApiResult<T> =
    | { ok: true; response: HttpResponse<T> }
    | { ok: false; error: HttpErrorResponse };

export interface ErrorAlert {
    errors: boolean;
    message: string;
}

export interface JobStatusStreamData {
    status: string;
    total: number;
}

export interface StartBackfillReturnData {
    job_id: string
}

export interface BackfillRequest {
    channel: string
}
