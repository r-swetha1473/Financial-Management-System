import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';

import { AuthService } from '../../../core/auth/auth.service';
import { hasPermission } from '../../../core/rbac/permissions';
import { ToastService } from '../../../core/ui/toast.service';
import { parseMoneyInput } from '../../../core/utils/money.util';
import { ConfirmDialogComponent } from '../../../shared/components/confirm-dialog/confirm-dialog.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { LoadingSkeletonComponent } from '../../../shared/components/loading-skeleton/loading-skeleton.component';
import { ModalComponent } from '../../../shared/components/modal/modal.component';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';
import { PaginationComponent } from '../../../shared/components/pagination/pagination.component';
import { StatusBadgeComponent } from '../../../shared/components/status-badge/status-badge.component';
import { InrPipe } from '../../../shared/pipes/inr.pipe';
import { FinanceBannerComponent } from '../components/finance-banner.component';
import { FinanceAccount, FinanceTransaction } from '../models/finance.model';
import { FinanceApiService } from '../services/finance-api.service';

@Component({
  selector: 'app-transaction-list-page',
  standalone: true,
  imports: [
    FormsModule,
    ReactiveFormsModule,
    PageHeaderComponent,
    FinanceBannerComponent,
    StatusBadgeComponent,
    PaginationComponent,
    ModalComponent,
    ConfirmDialogComponent,
    EmptyStateComponent,
    LoadingSkeletonComponent,
    InrPipe,
  ],
  templateUrl: './transaction-list.page.html',
})
export class TransactionListPage implements OnInit {
  private readonly api = inject(FinanceApiService);
  private readonly toast = inject(ToastService);
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthService);
  private readonly route = inject(ActivatedRoute);
  readonly canEdit = computed(() => hasPermission(this.auth.session()?.role, 'create'));
  readonly loading = signal(true);
  readonly error = signal('');
  readonly modalOpen = signal(false);
  readonly confirmOpen = signal(false);
  readonly saving = signal(false);
  items: FinanceTransaction[] = [];
  accounts: FinanceAccount[] = [];
  total = 0;
  page = 1;
  search = '';
  accountId = '';
  editing: FinanceTransaction | null = null;
  readonly form = this.fb.nonNullable.group({
    accountId: ['', Validators.required],
    transactionType: ['credit' as FinanceTransaction['transactionType'], Validators.required],
    amount: ['0.00', Validators.required],
    transactionDate: [new Date().toISOString().slice(0, 10), Validators.required],
    description: [''],
    referenceType: [''],
    referenceId: [''],
  });

  ngOnInit(): void {
    this.accountId = this.route.snapshot.queryParamMap.get('accountId') ?? '';
    this.api.listAccounts({ pageSize: 100 }).subscribe((result) => (this.accounts = result.items));
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.api.listTransactions({ page: this.page, search: this.search, accountId: this.accountId }).subscribe({
      next: (result) => {
        this.items = result.items;
        this.total = result.total;
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.error.set('Unable to load transactions.');
      },
    });
  }

  openCreate(): void {
    this.editing = null;
    this.form.reset({
      accountId: this.accountId,
      transactionType: 'credit',
      amount: '0.00',
      transactionDate: new Date().toISOString().slice(0, 10),
      description: '',
      referenceType: '',
      referenceId: '',
    });
    this.modalOpen.set(true);
  }

  requestSave(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.confirmOpen.set(true);
  }

  confirmSave(): void {
    const value = this.form.getRawValue();
    this.saving.set(true);
    this.api
      .saveTransaction({
        id: this.editing?.id,
        accountId: value.accountId,
        transactionType: value.transactionType,
        amount: parseMoneyInput(value.amount),
        transactionDate: value.transactionDate,
        description: value.description,
        referenceType: value.referenceType,
        referenceId: value.referenceId,
        reconciled: this.editing?.reconciled ?? false,
      })
      .subscribe({
        next: () => {
          this.saving.set(false);
          this.confirmOpen.set(false);
          this.modalOpen.set(false);
          this.toast.success('Transaction posted');
          this.load();
        },
        error: (err) => {
          this.saving.set(false);
          this.toast.error('Posting failed', err.message);
        },
      });
  }
}
