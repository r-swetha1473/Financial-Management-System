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
import { P2pBannerComponent } from '../components/p2p-banner.component';
import { Payable, SupplierInvoice, SupplierPayment } from '../models/p2p.model';
import { P2pApiService } from '../services/p2p-api.service';

@Component({
  selector: 'app-supplier-invoice-detail-page',
  standalone: true,
  imports: [RouterLink, PageHeaderComponent, P2pBannerComponent, StatusBadgeComponent, DocumentTrailComponent, EmptyStateComponent, InrPipe],
  templateUrl: './supplier-invoice-detail.page.html',
})
export class SupplierInvoiceDetailPage implements OnInit {
  private readonly api = inject(P2pApiService);
  private readonly route = inject(ActivatedRoute);
  private readonly auth = inject(AuthService);
  private readonly toast = inject(ToastService);

  readonly canEdit = computed(() => hasPermission(this.auth.session()?.role, 'create'));
  readonly canApprove = computed(() => hasPermission(this.auth.session()?.role, 'approve'));
  readonly deciding = signal(false);
  record: SupplierInvoice | null = null;
  payments: SupplierPayment[] = [];
  payable: Payable | null = null;
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
      ? this.api.approveSupplierInvoice(this.record.id)
      : this.api.rejectSupplierInvoice(this.record.id);
    request$.subscribe({
      next: (record) => {
        this.record = record;
        this.deciding.set(false);
        this.toast.success(approved ? 'Supplier invoice approved' : 'Supplier invoice rejected');
        this.reload();
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
      record: this.api.getSupplierInvoice(id),
      payments: this.api.listPayments({ pageSize: 100 }),
      payable: this.api.getPayable(id),
    }).subscribe({
      next: (data) => {
        this.record = data.record;
        this.payments = data.payments.items.filter((row) => row.supplierInvoiceId === id);
        this.payable = data.payable;
        this.outstanding = this.api.invoiceOutstanding(this.record, data.payments.items)?.outstanding ?? '0.00';
      },
      error: () => {
        this.record = null;
      },
    });
  }
}
