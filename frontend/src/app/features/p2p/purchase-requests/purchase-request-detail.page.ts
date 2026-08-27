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
import { P2pBannerComponent } from '../components/p2p-banner.component';
import { PurchaseOrder, PurchaseRequest } from '../models/p2p.model';
import { P2pApiService } from '../services/p2p-api.service';

@Component({
  selector: 'app-purchase-request-detail-page',
  standalone: true,
  imports: [
    RouterLink,
    PageHeaderComponent,
    P2pBannerComponent,
    StatusBadgeComponent,
    DocumentTrailComponent,
    EmptyStateComponent,
  ],
  templateUrl: './purchase-request-detail.page.html',
})
export class PurchaseRequestDetailPage implements OnInit {
  private readonly api = inject(P2pApiService);
  private readonly route = inject(ActivatedRoute);
  private readonly auth = inject(AuthService);
  private readonly toast = inject(ToastService);

  readonly canEdit = computed(() => hasPermission(this.auth.session()?.role, 'create'));
  readonly canApprove = computed(() => hasPermission(this.auth.session()?.role, 'approve'));
  readonly deciding = signal(false);
  record: PurchaseRequest | null = null;
  relatedOrders: PurchaseOrder[] = [];

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
      ? this.api.approvePurchaseRequest(this.record.id)
      : this.api.rejectPurchaseRequest(this.record.id);
    request$.subscribe({
      next: (record) => {
        this.record = record;
        this.deciding.set(false);
        this.toast.success(approved ? 'Purchase request approved' : 'Purchase request rejected');
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
      record: this.api.getPurchaseRequest(id),
      orders: this.api.listPurchaseOrders({ pageSize: 50 }),
    }).subscribe({
      next: (data) => {
        this.record = data.record;
        this.relatedOrders = data.orders.items.filter((order) => order.purchaseRequestId === id);
      },
      error: () => {
        this.record = null;
      },
    });
  }
}
