import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { JobStatusStreamData } from '../../types';



@Injectable({
  providedIn: 'root',
})
export class streamService {
    private baseURL = 'http://localhost:8000';

    private streamServiceTemplate<T>(url: string): Observable<T> {
        return new Observable<T>(observer => {
            const source = new EventSource(url); 

            source.onmessage = (event) => {
                try {
                    observer.next(JSON.parse(event.data) as T);
                } catch (e) {
                    observer.error(e);
                };
            };

            source.onerror = (error) => {
                observer.error(error);
                source.close();
            };

            return () => source.close();
        });
    };


    streamJobStatus(jobId:string): Observable<JobStatusStreamData> {
        const url = `${this.baseURL}/backfill-jobs/${jobId}/events`;
        console.log("url:", url)
        return this.streamServiceTemplate<JobStatusStreamData>(url);
    };


}
