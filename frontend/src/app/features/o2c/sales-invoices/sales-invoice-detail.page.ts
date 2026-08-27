import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';

import { AuthService } from '../../../core/auth/auth.service';
import { hasPermission } from '../../../core/rbac/permissions';
import { ToastService } from '../../../core/ui/toast.service';
import { DocumentTrailComponent } from '../../../shared/components/document-trail/document-trail.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';
import { StatusBadgeComponent } from '../../../shared/components/status-badge/status-badge.component';
import { InrPipe } from '../../../shared/pipes/inr.pipe';
import { O2cBannerComponent } from '../components/o2c-banner.component';
import { Collection, Receivable, SalesInvoice } from '../models/o2c.model';
import { O2cApiService } from '../services/o2c-api.service';

@Component({
  selector: 'app-sales-invoice-detail-page',
  standalone: true,
  imports: [RouterLink, PageHeaderComponent, O2cBannerComponent, StatusBadgeComponent, DocumentTrailComponent, EmptyStateComponent, InrPipe],
  templateUrl: './sales-invoice-detail.page.html',
})
export class SalesInvoiceDetailPage implements OnInit {
  private readonly api = inject(O2cApiService);
  private readonly route = inject(ActivatedRoute);
  private readonly auth = inject(AuthService);
  private readonly toast = inject(ToastService);
  readonly canEdit = computed(() => hasPermission(this.auth.session()?.role, 'create'));
  readonly canApprove = computed(() => hasPermission(this.auth.session()?.role, 'approve'));
  readonly deciding = signal(false);
  record: SalesInvoice | null = null;
  collections: Collection[] = [];
  receivable: Receivable | null = null;
  outstanding = '0.00';

  ngOnInit(): void {
    this.reload();
  }

  approve(): void {
    this.decide(true);
  }

  reject(): void {
    this.decide(false);
  }

  private decide(approved: boolean): void {
    if (!this.record) {
      return;
    }
    this.deciding.set(true);
    const request$ = approved
      ? this.api.approveSalesInvoice(this.record.id)
      : this.api.rejectSalesInvoice(this.record.id);
    request$.subscribe({
      next: (record) => {
        this.record = record;
        this.deciding.set(false);
        this.toast.success(approved ? 'Sales invoice approved' : 'Sales invoice rejected');
      },
      error: (err) => {
        this.deciding.set(false);
        this.toast.error('Decision failed', err.message);
      },
    });
  }

  private reload(): void {
    const id = this.route.snapshot.paramMap.get('id') ?? '';
    forkJoin({
      record: this.api.getSalesInvoice(id),
      collections: this.api.listCollections({ pageSize: 50 }),
      receivables: this.api.listReceivables({ pageSize: 50 }),
    }).subscribe({
      next: (data) => {
        this.record = data.record;
        this.collections = data.collections.items.filter((row) => row.salesInvoiceId === id);
        this.receivable = data.receivables.items.find((row) => row.sourceId === id) ?? null;
        this.outstanding = this.record?.outstanding ?? this.record?.amount ?? '0.00';
      },
      error: () => {
        this.record = null;
      },
    });
  }
}
