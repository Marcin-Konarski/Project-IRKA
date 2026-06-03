import { Pipe, PipeTransform } from "@angular/core";
import { DomSanitizer, SafeHtml } from "@angular/platform-browser";

@Pipe({
    name: "highlight",
    standalone: true,
})
export class HighlightPipe implements PipeTransform {
    constructor(private sanitizer: DomSanitizer) {}

    transform(text: string, query: string): SafeHtml {
        if (!query?.trim()) {
            return text;
        }

        const escapedQuery = query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
        const regex = new RegExp(`(${escapedQuery})`, "gi");
        const highlighted = text.replace(regex, '<span class="bg-black text-white rounded px-0.5">$1</span>');

        return this.sanitizer.bypassSecurityTrustHtml(highlighted);
    }
}
