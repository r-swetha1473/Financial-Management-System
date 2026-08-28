import { Component, OnDestroy, OnInit, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { forkJoin, of } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { DocumentsApiService } from '../../../core/api/documents-api.service';
import { AuthService } from '../../../core/auth/auth.service';
import { canMaintainReference } from '../../../core/rbac/permissions';
import { ToastService } from '../../../core/ui/toast.service';
import { DocumentTrailComponent } from '../../../shared/components/document-trail/document-trail.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { LoadingSkeletonComponent } from '../../../shared/components/loading-skeleton/loading-skeleton.component';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';
import { StatusBadgeComponent } from '../../../shared/components/status-badge/status-badge.component';
import { O2cBannerComponent } from '../../o2c/components/o2c-banner.component';
import { Booking, Customer, InvoiceReceipt, LegacyInvoice, PageResult, Quotation, SalesInvoice } from '../../o2c/models/o2c.model';
import { O2cApiService } from '../../o2c/services/o2c-api.service';

const EMPTY_PAGE: PageResult<never> = { items: [], total: 0, page: 1, pageSize: 20 };

@Component({
  selector: 'app-customer-detail-page',
  standalone: true,
  imports: [
    RouterLink,
    PageHeaderComponent,
    O2cBannerComponent,
    DocumentTrailComponent,
    StatusBadgeComponent,
    EmptyStateComponent,
    LoadingSkeletonComponent,
  ],
  templateUrl: './customer-detail.page.html',
})
export class CustomerDetailPage implements OnInit, OnDestroy {
  private readonly api = inject(O2cApiService);
  private readonly documents = inject(DocumentsApiService);
  private readonly route = inject(ActivatedRoute);
  private readonly auth = inject(AuthService);
  private readonly toast = inject(ToastService);
  readonly canEdit = computed(() => canMaintainReference(this.auth.session()?.role));
  readonly loading = signal(true);
  customer: Customer | null = null;
  quotations: Quotation[] = [];
  invoices: SalesInvoice[] = [];
  bookings: Booking[] = [];
  legacyInvoices: LegacyInvoice[] = [];
  receipts: InvoiceReceipt[] = [];
  readonly photoUrl = signal<string | null>(null);

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id') ?? '';
    forkJoin({
      customer: this.api.getCustomer(id).pipe(catchError(() => of(null))),
      quotations: this.api.listQuotations({ customerId: id, pageSize: 20 }).pipe(catchError(() => of(EMPTY_PAGE))),
      invoices: this.api.listSalesInvoices({ customerId: id, pageSize: 20 }).pipe(catchError(() => of(EMPTY_PAGE))),
    }).subscribe((data) => {
      this.customer = data.customer;
      this.quotations = data.quotations.items;
      this.invoices = data.invoices.items;
      this.loading.set(false);
      const photoId = data.customer?.photoDocumentId;
      if (photoId) {
        this.documents.getContent(photoId).subscribe((blob) => {
          this.revokePhoto();
          this.photoUrl.set(URL.createObjectURL(blob));
        });
      }
    });
  }

  ngOnDestroy(): void {
    this.revokePhoto();
  }

  openAddressProof(): void {
    const documentId = this.customer?.addressProofDocumentId;
    if (!documentId) {
      return;
    }
    this.documents.getContent(documentId).subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        window.open(url, '_blank', 'noopener');
      },
      error: (err) => this.toast.error('Unable to open address proof', err.message),
    });
  }

  private revokePhoto(): void {
    const url = this.photoUrl();
    if (url) {
      URL.revokeObjectURL(url);
      this.photoUrl.set(null);
    }
  }
}
