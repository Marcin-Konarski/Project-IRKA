import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { JobStatusStreamData } from '../../types';
import { UserState } from '../state/userState';



@Injectable({
  providedIn: 'root',
})
export class streamService {
    private baseURL = 'http://localhost:8000';
    private userState = inject(UserState);

    private streamServiceTemplate<T>(url: string): Observable<T> {
        return new Observable<T>(observer => {
            const source = new EventSource(url); 

            source.onmessage = (event) => {
                try {
                    console.log("SSE message:", url, event.data);
                    observer.next(JSON.parse(event.data) as T);
                } catch (e) {
                    observer.error(e);
                };
            };

            source.onerror = (error) => {
                console.error("SSE error:", url, error);
                observer.error(error);
                source.close();
            };

            return () => source.close();
        });
    };


    streamJobStatus(jobId:string): Observable<JobStatusStreamData> {
        const token = this.userState.accessToken();
        const query = token ? `?access_token=${encodeURIComponent(token)}` : "";
        const url = `${this.baseURL}/backfill-jobs/${jobId}/events${query}`;
        console.log("url:", url)
        return this.streamServiceTemplate<JobStatusStreamData>(url);
    };


}
