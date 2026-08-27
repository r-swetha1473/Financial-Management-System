import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';

import { AuthService } from '../../../core/auth/auth.service';
import { hasPermission } from '../../../core/rbac/permissions';
import { ToastService } from '../../../core/ui/toast.service';
import { parseMoneyInput } from '../../../core/utils/money.util';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { LoadingSkeletonComponent } from '../../../shared/components/loading-skeleton/loading-skeleton.component';
import { ModalComponent } from '../../../shared/components/modal/modal.component';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';
import { PaginationComponent } from '../../../shared/components/pagination/pagination.component';
import { InrPipe } from '../../../shared/pipes/inr.pipe';
import { FinanceBannerComponent } from '../components/finance-banner.component';
import { Expense } from '../models/finance.model';
import { FinanceApiService } from '../services/finance-api.service';
import { Vendor } from '../../p2p/models/p2p.model';
import { P2pApiService } from '../../p2p/services/p2p-api.service';

@Component({
  selector: 'app-expense-list-page',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    RouterLink,
    PageHeaderComponent,
    FinanceBannerComponent,
    PaginationComponent,
    ModalComponent,
    EmptyStateComponent,
    LoadingSkeletonComponent,
    InrPipe,
  ],
  templateUrl: './expense-list.page.html',
})
export class ExpenseListPage implements OnInit {
  private readonly api = inject(FinanceApiService);
  private readonly p2p = inject(P2pApiService);
  private readonly toast = inject(ToastService);
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthService);
  readonly canEdit = computed(() => hasPermission(this.auth.session()?.role, 'create'));
  readonly loading = signal(true);
  readonly error = signal('');
  readonly modalOpen = signal(false);
  readonly saving = signal(false);
  items: Expense[] = [];
  vendors: Vendor[] = [];
  total = 0;
  page = 1;

  readonly form = this.fb.nonNullable.group({
    vendorId: [''],
    productServiceName: [''],
    cost: ['0.00', Validators.required],
    expenseDate: [new Date().toISOString().slice(0, 10), Validators.required],
  });

  ngOnInit(): void {
    this.p2p.listVendors({ pageSize: 100 }).subscribe((result) => (this.vendors = result.items));
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.api
      .listExpenses({
        page: this.page,
      })
      .subscribe({
        next: (result) => {
          this.items = result.items;
          this.total = result.total;
          this.loading.set(false);
        },
        error: () => {
          this.loading.set(false);
          this.error.set('Unable to load expenses.');
        },
      });
  }

  openCreate(): void {
    this.form.reset({
      vendorId: '',
      productServiceName: '',
      cost: '0.00',
      expenseDate: new Date().toISOString().slice(0, 10),
    });
    this.modalOpen.set(true);
  }

  openEdit(_row: Expense): void {
    this.toast.error('Updating an expense is not supported by the API yet.');
  }

  save(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const value = this.form.getRawValue();
    this.saving.set(true);
    this.api
      .saveExpense({
        vendorId: value.vendorId || null,
        categoryId: null,
        subcategoryId: null,
        productId: null,
        productServiceName: value.productServiceName,
        sku: '',
        quantity: '1.00',
        unitPrice: '0.00',
        cost: parseMoneyInput(value.cost),
        gstPercentage: '0.00',
        gstAmount: '0.00',
        purchaseOrderNumber: '',
        expenseDate: value.expenseDate,
        status: 'approved',
      })
      .subscribe({
        next: () => {
          this.saving.set(false);
          this.modalOpen.set(false);
          this.toast.success('Expense recorded');
          this.load();
        },
        error: (err) => {
          this.saving.set(false);
          this.toast.error('Save failed', err.message);
        },
      });
  }
}
