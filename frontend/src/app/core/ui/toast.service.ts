import { Injectable, signal } from '@angular/core';

export type ToastKind = 'success' | 'error' | 'info';

export interface ToastMessage {
  id: number;
  kind: ToastKind;
  title: string;
  body?: string;
}

@Injectable({ providedIn: 'root' })
export class ToastService {
  private nextId = 1;
  readonly toasts = signal<ToastMessage[]>([]);

  success(title: string, body?: string): void {
    this.push('success', title, body);
  }

  error(title: string, body?: string): void {
    this.push('error', title, body);
  }

  info(title: string, body?: string): void {
    this.push('info', title, body);
  }

  dismiss(id: number): void {
    this.toasts.update((items) => items.filter((item) => item.id !== id));
  }

  private push(kind: ToastKind, title: string, body?: string): void {
    const id = this.nextId++;
    this.toasts.update((items) => [...items, { id, kind, title, body }]);
    window.setTimeout(() => this.dismiss(id), 4200);
  }
}
