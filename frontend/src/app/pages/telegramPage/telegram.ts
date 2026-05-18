import { Component, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../core/http/apiService';

@Component({
  selector: 'app-telegram',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './telegram.html',
  styleUrls: ['./telegram.css']
})
export class TelegramComponent {
  private apiService = inject(ApiService);
  private router = inject(Router);

  phone = '';
  code = '';
  phoneCodeHash = '';
  codeRequested = signal(false);
  loading = signal(false);
  error = signal('');

  async requestCode() {
    if (!this.phone) {
      this.error.set('Please enter a phone number');
      return;
    }

    this.loading.set(true);
    this.error.set('');

    const result = await this.apiService.requestTelegramCode(this.phone);
    
    if (result.ok) {
      const data = result.response?.body as any;
      this.phoneCodeHash = data.phone_code_hash;
      this.codeRequested.set(true);
    } else {
      this.error.set(result.error?.error?.detail || result.error?.error?.error || 'Failed to send code');
    }
    
    this.loading.set(false);
  }

  async verifyCode() {
    const normalizedCode = this.code.trim();
    if (!/^\d{5,6}$/.test(normalizedCode)) {
      this.error.set('Please enter a valid 5- or 6-digit code');
      return;
    }

    this.loading.set(true);
    this.error.set('');

    const result = await this.apiService.verifyTelegramCode(
      this.phone,
      normalizedCode,
      this.phoneCodeHash
    );

    if (result.ok) {
      // Success - redirect to home or next page
      this.router.navigate(['/']);
    } else {
      this.error.set(result.error?.error?.detail || result.error?.error?.error || 'Invalid code');
    }

    this.loading.set(false);
  }

  backToPhone() {
    this.codeRequested.set(false);
    this.code = '';
    this.error.set('');
  }
}
