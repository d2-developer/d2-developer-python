from genericpath import exists
import imp
import json
import os
import sys, os
import logging
import csv
from django.urls import reverse
from django.utils import timezone
from BINANCE.order import cancel_active_order

from binance.client import Client
from django.contrib import messages
from django.shortcuts import render
from rest_framework import generics
from django.urls import reverse_lazy
from django.http import JsonResponse
from cryptography.fernet import Fernet
from django.http import HttpResponse
from BINANCE.models import BinanceCommand
from mixins import SimpleOTPPassesTestMixin                                   
from django.core.serializers import serialize
from django.contrib.auth import get_user_model
from django.views.generic.base import TemplateView
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from BINANCE.serializers import BinanceCommandSerializer
from django.views.generic import (UpdateView, CreateView)
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import CreateView, ListView, UpdateView, DeleteView, DetailView
from BINANCE.models import Allocation, Binance, Binance_GroupOrder, Binance_Risk_Management, BinanceCommand, BinanceGroup, BinanceSymbol, Customer, Secret, Wallet, Binance_Logs
from BINANCE.forms import AllocationForm, Binance_GroupForm, BinanceForm, BinanceFormEdit, BinanceGroupOrderForm, BinanceOrderForm, BinanceReportForm, CustomerForm, SecretForm, WalletDetailForm, WalletForm
# from django_otp.decorators import otp_required
from . utils import *
from BINANCE import utils
from BINANCE import models

logger_binance = logging.getLogger('binance')


User = get_user_model()
# @login_required
# @otp_required
def customers_flat_list(request):

    return render(request,'customers_flat_list.html', context={'customers': Binance.objects.all()})


@login_required
def customers_flat_details(request, pk):

    customer = Binance.objects.get(pk=pk)
    return render(request,'customers_flat_details.html',context={'customer': customer})

@login_required
def new_customer(request):
    user = User.objects.first() 
    if request.method == 'POST':
        key_id = request.POST['key_id']
        secret_id = request.POST['secret_id']

        form = BinanceForm(request.POST)
        if form.is_valid():
            instance = form.save(commit=False)

            user_key = os.getenv('USER_KEY')
            encoded_key = bytes(user_key,'UTF-8')
            fernet = Fernet(encoded_key)
            key = fernet.encrypt(key_id.encode())
            secret = fernet.encrypt(secret_id.encode())
            print(">>>>>>>>>>>>>>>>>>>>>>",key)
            instance.key_id =  key
            instance.secret_id = secret
            instance.save()

            messages.success(request, 'Customer created successfully')
            return redirect('binances:customers_flat_list')
    else:
        form = BinanceForm()
    return render(request,'new_customer.html', {'form': form})


@login_required
def update_new_customer(request,pk):
    print(">>>>>>>>>>>>>>> pk ",pk)
    user = Binance.objects.get(id = pk)
    if request.method == 'POST':
        form = BinanceFormEdit(request.POST, instance = user)
        if form.is_valid():
            key_id = form.data.get('key_id')
            key_secret = form.data.get('secret_id')
            is_paper_account = form.data.get('is_paper_account')
            check_box = form.data.get('check_box')
            risk_management = form.data.get('risk_management')
            leverage = form.data.get("set_leverage")
            print("leverage  data +++++++++++",leverage)
            leverage_value = form.data.get("leverage")
            print("leverage  data +++++++++++ leverage_value",leverage_value)
            instance = form.save(commit=False)
            if leverage == "on":
                instance.leverage = leverage_value
            if check_box is None:
                instance.position = 0
                instance.position_value  = None
            # if risk_management is None:
            #     instance.risk_management = 0
            #     instance.per_trade_stop_loss  = None
            #     instance.per_day_max_loss  = None
            #     instance.maximum_SL  = None
            is_testnet = False
            if is_paper_account == "on":
                is_testnet = True
            else:
                is_testnet = False
            try:
                client = Client(str(key_id), str(key_secret), tld='com', testnet= is_testnet)
                summary = client.futures_account(recvWindow = 5000000)
                client.futures_change_leverage(symbol="ETHUSDT",leverage=leverage_value)

                user_key = os.getenv('USER_KEY')
                encoded_key = bytes(user_key,'UTF-8')
                fernet = Fernet(encoded_key)
                key = fernet.encrypt(key_id.encode())
                secret = fernet.encrypt(key_secret.encode())
                instance.key_id = key
                instance.secret_id = secret
                instance.summary = summary
                instance.save()
            except Exception as e:
                exc_type, exe_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                logger_binance.error(exc_type,fname, exc_tb.tb_lineno, str(e))
                logger_binance.exception(str(e))
                print(">>>>>>>>>>>e",e)
                messages.error(request, "Invalid Credentials")
                return redirect('binances:edit_customer',pk)
     
            messages.success(request, 'Customer Updated successfully')
            return redirect('binances:customers_flat_list')
    else:
        form = BinanceFormEdit(instance = user)
    return render(request,'new_customer.html', {'form': form , 'binance':user})


@method_decorator(login_required, name='dispatch')
class WalletUpdateView(CreateView):
    model = Binance
    pk_url_kwarg = 'pk'
    context_object_name = 'customer'
    form_class = BinanceForm

    success_url = reverse_lazy('customers_flat_list')

@method_decorator(login_required, name='dispatch')
class BinacneDetailView(DetailView):
    model = Binance
    template_name = 'binance_detail.html'
    def get_context_data(self, **kwargs):
        context = super(BinacneDetailView,self).get_context_data(**kwargs)
        return context

@login_required
@csrf_exempt
def binance_show_balance(request):
    key_id = request.POST['key_id']
    instance = Binance.objects.get(key_id = key_id)
    key_id = decrypt_keyids(key_id)
    secret_id = request.POST['secret_id']
    secret_id = decrypt_binance(secret_id)
    is_paper_account = request.POST['is_paper_account']
    is_testnet = True  if is_paper_account == "True" else False
    try:
        client = Client(str(key_id), str(secret_id), tld='com', testnet= is_testnet)
        summary = client.futures_account(recvWindow = 5000000)
        leverage = client.futures_change_leverage(symbol="ETHUSDT",leverage="3")
        print(">>>>> leverage",summary)
        instance.summary = summary
        instance.save()
        
    except Exception as e:
        exc_type, exe_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        logger_binance.error(exc_type,fname, exc_tb.tb_lineno, str(e))
        logger_binance.exception(str(e))
        print(">>>>>>>> Exception",e)
    return JsonResponse({'type':'success',"res":summary})



@login_required
@csrf_exempt
def clear_group(request):
    group_id = request.POST['group_id']
    BinanceGroup.objects.filter(id=group_id).delete()
    return JsonResponse({'type':'success'})      


@login_required
@csrf_exempt
def delete_user(request):
    id = request.POST['id']
    Binance.objects.filter(id=id).delete()
    return JsonResponse({'type':'success'})         


@login_required
def report_for_binance(request, pk):
    user = Binance.objects.get(id=pk)
    client = Client(str(decrypt_keyids(user.key_id)), str(decrypt_binance(user.secret_id)), tld='com', testnet= user.is_paper_account)
    binance_name = Binance.objects.get(pk=pk).binance_name
    if request.method == "POST":
        report_form = BinanceReportForm(request.POST)
        if report_form.is_valid():
            try:
                # reports = client.futures_account_trades(symbol ="ETHUSDT",limit="100")
                report = client.futures_get_all_orders(symbol=report_form.cleaned_data.get("symbol"),limit="100")
                # reports = client.futures_income_history(symbol=report_form.cleaned_data.get("symbol"),limit="100")
                # reports = client.futures_historical_klines(symbol ="ETHUSDT" ,interval="1M", start_str="1661340366826", end_str="1661408080088",limit="100")
                # print(">-*/-/-*/-*/-*/ report data",reports)
                # report = client.futures_recent_trades(symbol = report_form.cleaned_data.get("symbol"), limit = report_form.cleaned_data.get("type"))
            except Exception as e:
                exc_type, exe_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                logger_binance.error(exc_type,fname, exc_tb.tb_lineno, str(e))
                logger_binance.exception(str(e))
                print("exception a se +++++++ in report",e)
                report = None
            return render(request,'binance_report_form.html',{'report_form': report_form,'pk': pk,'binance_name': binance_name,'report': report,})
    else:
        report_form = BinanceReportForm()
    return render(request,'binance_report_form.html',{'report_form': report_form,'pk': pk,'binance_name': binance_name})



@method_decorator(login_required, name='dispatch')
class Binance_GroupsListView(ListView):
    model = BinanceGroup
    template_name = 'binance_groups_list.html'


@method_decorator(login_required, name='dispatch')
class Binance_GroupDetailView(DetailView):
    model = BinanceGroup
    template_name = 'binance_groupDetails.html'

    def get_context_data(self, **kwargs):
        context = super(
            Binance_GroupDetailView,
            self).get_context_data(**kwargs)
        return context


@method_decorator(login_required, name='dispatch')
class GroupDeleteView(DeleteView):
    model = BinanceGroup
    success_url = reverse_lazy('binance_groups_list')


@login_required
def binance_group_create(request):
    # mdl = BinanceGroup.objects.all()
    mdl = ""
    if request.method == 'POST':
        form = Binance_GroupForm(request.POST)
        g_name = request.POST['name']
        print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>",g_name)
        if form.is_valid():
            form.save(commit=False)
            try:
                print(">>>> in try")
                gname = BinanceGroup.objects.get(name=str(g_name))
                messages.error(request, 'Group Already register')
                return redirect ('binances:binance_groups_list')
            except Exception as e:
                exc_type, exe_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                logger_binance.error(exc_type,fname, exc_tb.tb_lineno, str(e))
                logger_binance.exception(str(e))
                print(">>>> in except")
                form.save(commit=True)
            messages.success(request, 'Binance Group created successfully')
            return redirect('binances:binance_groups_list')
    else:
        form = Binance_GroupForm()
        return render(request, 'binance_group_form.html',{'form':form,'group':mdl})

@login_required
def Binance_GroupUpdate(request,pk):
    mdl = BinanceGroup.objects.get(pk=pk)
    group_instance = BinanceGroup.objects.get(id = pk)
    if request.method == 'POST':
        form = Binance_GroupForm(request.POST,instance = group_instance)
        if form.is_valid():
            data = form.save()
            messages.success(request, 'Binance Group Updated successfully')
            return redirect('binances:binance_groups_list')
    else:
        form = Binance_GroupForm(instance = group_instance)
        return render(request, 'binance_group_form.html',{'form':form,'group':group_instance})

@login_required
def binance_secret_update(request,pk):
    group_instance = get_object_or_404(BinanceGroup,id = pk)
    group_instance.secret_key = request.POST['secret_key']
    group_instance.save()
    messages.success(request, 'Secret Key Updated successfully')
    return redirect ('binances:binance_groups_list')


class WizardHomeView(TemplateView):
    template_name = "wizard/wizard_home.html"                    

class WizardCustomerCreateView(CreateView):

    model = Binance
    form_class = BinanceForm
    success_url = reverse_lazy('binances:wizard_wallets_list')
    template_name = 'wizard/wizard_customer.html'
    def form_valid(self, form):
        
        key_id = form.data.get('key_id')
        key_secret = form.data.get('secret_id')
        is_paper_account = form.data.get('is_paper_account')
        leverage_value = form.data.get('leverage')
        try:
            for data in  Binance.objects.all():
                api_key=decrypt_keyids(data.key_id)
                api_secret=decrypt_binance(data.secret_id)
                if str(api_key) == str(key_id) or str(api_secret) == str(key_secret):
                    messages.error(self.request, "Same User Exists")
                    return redirect('binances:wizard_customer')
        except:
            check = Binance.objects.filter(key_id=key_id)
            if check.exists():
                messages.error(self.request, "Same User Exists")
                return redirect('binances:wizard_customer')
        try:
            is_testnet = False
            if is_paper_account == "on":
                is_testnet = True
            else:
                is_testnet = False
            client = Client(str(key_id), str(key_secret), tld='com', testnet= is_testnet)
            summary = client.futures_account_balance(recvWindow = 5000000)
            summary= [item for item in summary if item.get('asset')=="USDT"]
            summary = summary[0]
            client.futures_change_leverage(symbol="ETHUSDT",leverage=leverage_value)
            user_key = os.getenv('USER_KEY')
            encoded_key = bytes(user_key,'UTF-8')
            fernet = Fernet(encoded_key)
            key = fernet.encrypt(key_id.encode())
            secret = fernet.encrypt(key_secret.encode())
            instance = form.save(commit=False)
            print("summary>>>>", summary)
            instance.key_id = key
            instance.secret_id = secret
            instance.summary = summary
            instance.leverage = leverage_value
            instance.intial_balance = summary['balance']
            instance.daily_initial_balance = summary['balance']
            instance.save()
            return super().form_valid(form)
        except Exception as e:
            print(">>>>>>>>>>e", e)
            exc_type, exe_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            logger_binance.error(exc_type,fname, exc_tb.tb_lineno, str(e))
            logger_binance.exception(str(e))
            messages.error(self.request, "Invalid Credentials")
            return redirect('binances:wizard_customer')

    def get_success_url(self):
        # return reverse('binances:wizard_wallets_list', args=(self.object.id,))
        return reverse('binances:customers_flat_list')


class WizardCustomerUpdateView(UpdateView):
    model = Customer
    form_class = BinanceFormEdit
    success_url = reverse_lazy('wizard_wallets_list')
    template_name = 'wizard/wizard_customer.html'

    def form_valid(self, form):
        key_id = form.data.get('key_id')
        key_secret = form.data.get('secret_id')
        is_paper_account = form.data.get('is_paper_account')
        
        try:
            check = Binance.objects.get(key_id=key_id)
            if check.exists():
                messages.error(self.request, "Same User Exists")
                return redirect('binances:wizard_wallets_list')
        except:
            check = Binance.objects.filter(key_id=key_id)
            if check.exists():
                messages.error(self.request, "Same User Exists")
                return redirect('binances:wizard_wallets_list')
        
        user_key = os.getenv('USER_KEY')
        encoded_key = bytes(user_key,'UTF-8')
        fernet = Fernet(encoded_key)
        key = fernet.encrypt(key_id.encode())
        secret = fernet.encrypt(key_secret.encode())
        instance = form.save(commit=False)
        
        try:
            instance.key_id = key
            instance.key_secret = secret
            instance.save()
            return super().form_valid(form)
        except Exception as e:
            messages.error(self.request, "Invalid Credentials")
            exc_type, exe_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            logger_binance.error(exc_type,fname, exc_tb.tb_lineno, str(e))
            logger_binance.exception(str(e))
            return redirect('binances:wizard_wallets_list')

    def get_success_url(self):
        return reverse('binances:wizard_wallets_list', args=(self.object.id,))



class WizardWalletsListView(ListView):
    model = Wallet
    context_object_name = 'wizard_wallets_list'
    template_name = 'wizard/wizard_wallets_list.html'

    def get_queryset(self):
        self.customer = get_object_or_404(Binance, pk=self.kwargs['customer_pk'])
        return Wallet.objects.filter(customer=self.customer)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customer_pk'] = self.kwargs['customer_pk']
        return context


class WizardWalletCreateView(CreateView):
    model = Wallet
    form_class = WalletDetailForm
    customer_pk_kwarg = 'customer_pk'
    wallet_pk_kwarg = 'wallet_pk'
    success_url = reverse_lazy('binances:wizard_wallets_list')
    template_name = 'wizard/wizard_wallet_form.html'

    class Meta:
        pass

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customer_pk'] = self.kwargs['customer_pk']
        return context

    def get_initial(self):
        customer = get_object_or_404(Binance, id=self.kwargs.get('customer_pk'))
        return {'customer': customer,}

    def get_success_url(self):
        return reverse('binances:wizard_wallets_list', args=(self.object.customer.id,))


class WizardWalletUpdateView(UpdateView):
    model = Wallet
    form_class = WalletDetailForm
    success_url = reverse_lazy('binances:wizard_wallets_list')
    template_name = 'wizard/wizard_wallet_form.html'

    def get_success_url(self):
        return reverse('binances:wizard_wallets_list', args=(self.object.customer.id,))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customer_pk'] = self.kwargs['customer_pk']
        context['wallet_pk'] = self.kwargs['pk']
        return context

class WizardSecretListView(ListView):
    model = Secret
    context_object_name = 'wizard_secrets_list'
    template_name = 'wizard/wizard_secrets_list.html'

    def get_queryset(self):
        self.wallet = get_object_or_404(Wallet, pk=self.kwargs['wallet_pk'])
        return Secret.objects.filter(container=self.wallet)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customer_pk'] = self.kwargs['customer_pk']
        context['wallet_pk'] = self.kwargs['wallet_pk']
        return context


class WizardSecretUpdateView(UpdateView):
    model = Secret
    form_class = SecretForm
    success_url = reverse_lazy('binances:wizard_secrets_list')
    template_name = 'wizard/wizard_secret_form.html'

    def get_success_url(self):

        print(f"153: {self.object}")
        print(f"153: {self.object.container.customer}")
        print(f"153: {self.object.container.customer.id}")
        print(f"153: {self.object.container.id}")

        return reverse('binances:wizard_secrets_list', args=(self.object.container.customer.id,self.object.container.id,))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customer_pk'] = self.kwargs['customer_pk']
        context['wallet_pk'] = self.kwargs['wallet_pk']
        return context


class WizardSecretCreateView(CreateView):
    model = Secret
    form_class = SecretForm
    success_url = reverse_lazy('binances:wizard_secrets_list')
    template_name = 'wizard/wizard_secret_create_form.html'

    class Meta:
        pass

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customer_pk'] = self.kwargs['customer_pk']
        context['wallet_pk'] = self.kwargs['wallet_pk']
        return context

    def get_initial(self):
        container = get_object_or_404(Wallet, id=self.kwargs.get('wallet_pk'))
        return {'container': container,}

    def get_success_url(self):
        return reverse(
            'binances:wizard_secrets_list',
            args=(self.object.container.customer.id,self.object.container.id,))

class WizardAllocationsListView(ListView):
    model = Allocation
    context_object_name = 'wizard_allocations_list'
    template_name = 'wizard/wizard_allocations_list.html'

    def get_queryset(self):
        self.wallet = get_object_or_404(Wallet, pk=self.kwargs['wallet_pk'])
        return Allocation.objects.filter(wallet=self.wallet)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customer_pk'] = self.kwargs['customer_pk']
        context['wallet_pk'] = self.kwargs['wallet_pk']
        return context

class WizardAllocationUpdateView(UpdateView):
    model = Allocation
    form_class = AllocationForm
    success_url = reverse_lazy('binances:wizard_allocations_list')
    template_name = 'wizard/wizard_allocation_form.html'

    def get_success_url(self):

        return reverse('binances:wizard_allocations_list', args=(self.object.wallet.customer.id,self.object.wallet.id,))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customer_pk'] = self.kwargs['customer_pk']
        context['wallet_pk'] = self.kwargs['wallet_pk']
        return context

class WizardAllocationCreateView(CreateView):
    model = Allocation
    form_class = AllocationForm
    success_url = reverse_lazy('binances:wizard_allocations_list')
    template_name = 'wizard/wizard_allocation_create_form.html'
    class Meta:
        pass

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customer_pk'] = self.kwargs['customer_pk']
        context['wallet_pk'] = self.kwargs['wallet_pk']
        return context

    def get_initial(self):
        wallet = get_object_or_404(Wallet, id=self.kwargs.get('wallet_pk'))
        return {'wallet': wallet,}

    def get_success_url(self):
        return reverse('binances:wizard_allocations_list',args=(self.object.wallet.customer.id,self.object.wallet.id,))

class WizardAllocationDeleteView(DeleteView):
    model = Allocation
    success_url = reverse_lazy('binances:wizard_allocations_list')
    template_name = 'wizard/wizard_confirm_delete.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customer_pk'] = self.kwargs['customer_pk']
        context['wallet_pk'] = self.kwargs['wallet_pk']
        return context

    def get_success_url(self):

        return reverse('binances:wizard_allocations_list', args=(
            self.object.wallet.customer.id,
            self.object.wallet.id,))


class WalletListView(ListView):
    model = Wallet
    context_object_name = 'wallets'

class WalletCreateView(CreateView):
    model = Wallet
    form_class = WalletForm
    success_url = reverse_lazy('wallets_list')

class WalletUpdateView(UpdateView):
    model = Wallet
    form_class = WalletForm
    success_url = reverse_lazy('wallets_list')

class SecretCreateView(CreateView):
    model = Secret
    form_class = SecretForm
    wallet_pk_kwarg = 'wallet_pk'

    print(f'SecretCreateView wallet_pk_kwarg: {wallet_pk_kwarg}')

    success_url = reverse_lazy('wallets_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['wallet_pk'] = self.kwargs['wallet_pk']  
        return context

class SecretUpdateView(UpdateView):
    model = Secret
    form_class = SecretForm
    success_url = reverse_lazy('wallets_list')

class SecretListView(ListView):
    model = Secret

    context_object_name = 'secrets'

    def get_queryset(self):
        self.wallet = get_object_or_404(Wallet, pk=self.kwargs['wallet_pk'])
        return Secret.objects.filter(container=self.wallet)

@login_required
def place_order_binance(request, pk):
    binance_name = Binance.objects.get(pk=pk).binance_name
    if request.method == "POST":
        form = BinanceOrderForm(request.POST)
        if form.is_valid():
            symbol_id = form.cleaned_data.get("symbol_id")
            order = form.save(commit=False)
            order.created_by = request.user
            order.binance = Binance.objects.get(pk=pk)
            order.save()
            messages.success(request, 'Order placed.')
            return redirect('binances:binance_details', pk=pk)
            # return JsonResponse({'type':'success'})
    else:
        form = BinanceOrderForm()
        form.fields['binance'].initial = Binance.objects.get(pk=pk)
        form.fields['created_by'].initial = request.user

    return render(request,'binance_order_form.html',{'form': form, 'binance_name': binance_name, 'pk': pk})

class BinanceCommandList(generics.ListCreateAPIView):
    queryset = BinanceCommand.objects.all()
    serializer_class = BinanceCommandSerializer

class BinanceCommandDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = BinanceCommand.objects.all()
    serializer_class = BinanceCommandSerializer


@login_required
def binance_make_order(request):
    symbol = BinanceSymbol.objects.all()
    groups = BinanceGroup.objects.all()
    return render(request,'binance_group_order_form.html',{'symbol': symbol,'groups':groups})

@login_required
def start_stop_group(request, pk, act):
    investor = BinanceGroup.objects.get(pk=pk)
    is_disabled = True if act == 'stop' else False
    investor.is_disabled = is_disabled
    investor.save()
    return redirect('binances:binance_groups_list')

@login_required
def start_stop_Binance(request, pk, act):
    investor = Binance.objects.get(pk=pk)
    is_disabled = True if act == 'stop' else False
    investor.is_disabled = is_disabled
    investor.save()
    return redirect('binances:customers_flat_list')


@login_required
def stop_all_binance(request):
    binance = Binance.objects.all()
    for e in binance:
        e.is_disabled = True
        e.save()
    return redirect('binances:customers_flat_list')

@login_required
def start_all_binance(request):
    binance = Binance.objects.all()
    for e in binance:
        e.is_disabled = False
        e.save()
    return redirect('binances:customers_flat_list')

@login_required
def stop_all_groups(request):
    binance = BinanceGroup.objects.all()
    for e in binance:
        e.is_disabled = True
        e.save()
    return redirect('binances:binance_groups_list')

@login_required
def start_all_groups(request):
    binance = BinanceGroup.objects.all()
    for e in binance:
        e.is_disabled = False
        e.save()
    return redirect('binances:binance_groups_list')

@login_required
@csrf_exempt
def binance_group_order_clear(request):
    id = request.POST.get('group_user_id')
    Binance_GroupOrder.objects.filter(user_id = id).delete()
    return JsonResponse({'type':'success'})

@login_required
@csrf_exempt
def get_binance_logs(request):
    user_id = request.POST ['user_id']
    logs_data = Binance_Logs.objects.filter(user_id = user_id, status=False).order_by('-created_at')
    logs_data_serialize = serialize('json',logs_data)
    return JsonResponse({'type':'success',"res":logs_data_serialize})

@login_required
@csrf_exempt
def binance_clear_logs(request):
    user_id = request.POST ['user_id']
    binance = Binance_Logs.objects.filter(user_id=user_id)
    binance.update(status=True)
    return JsonResponse({'type':'success'})


@login_required
def binanceSymbol(request):
    symbolData = BinanceSymbol.objects.all()
    return render(request,'binance_symbols.html',{'symbolData': symbolData})

@login_required
@csrf_exempt
def binance_symbol_update(request):
    print("???????????????>>>>>>>>",request.POST['symbol'])
    group_instance = get_object_or_404(BinanceSymbol,id = request.POST['symbol_id'])
    group_instance.symbol_id = request.POST['symbol']
    group_instance.save()
    messages.success(request, 'Symbol Updated successfully')
    # return redirect ('ftx:BinanceSymbol')
    return JsonResponse({'type':'success'})


@login_required
@csrf_exempt
def SymbolForm_create(request):
    symbol = request.POST['symbol']
    try:
        data = BinanceSymbol.objects.get(symbol_id = symbol)
        if str(data) == str(symbol):
            return JsonResponse({'type':'error'})
    except:
        data = BinanceSymbol.objects.create(symbol_id = symbol)
        # symbol_data = BinanceSymbol.objects.all().last()
        # symbol_data_serialize = serialize('json',symbol_data)
        return JsonResponse({'type':'success'})

@login_required
@csrf_exempt
def SymbolForm_delete(request):
    symbol = request.POST['symbol_id']
    print(">>>>>>>>>>>. symbol",symbol)
    BinanceSymbol.objects.get(id=symbol).delete()
    return JsonResponse({'type':'success'})



def update_daily_balance(request):
    users = Binance.objects.filter(per_day_max_loss__gte =  1)
    if len(users)> 0:
        for user in users:
            print("user>>>>>", user)
            # UPDATE THE CURRENT FUND AMOUNT
            try:
                if user.is_paper_account == True:
                    is_testnet = True
                else:
                    is_testnet = False
                client = Client(str(decrypt_keyids(user.key_id)), str(decrypt_binance(user.secret_id)), tld='com', testnet= is_testnet)
                summary = client.futures_account_balance(recvWindow = 5000000)
                summary= [item for item in summary if item.get('asset')=="USDT"]
                summary = summary[0]

                Binance.objects.filter(id = user.id).update(daily_initial_balance = summary['balance'], daily_updated_at= timezone.now())
            except Exception as e:
                exc_type, exe_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                logger_binance.error(exc_type,fname, exc_tb.tb_lineno, str(e))
                logger_binance.exception(str(e))
                print("eeee>>>>>", e)
    return HttpResponse("Function Completed Successfully")


def restart_daily_accounts(request):
    try:
        accounts = Binance.objects.filter(risk_type="2")
        print(accounts)
        if len(accounts)> 0:
            for account in accounts:
                Binance.objects.filter(id = account.user_id).update(is_disabled = False)
                Binance_Risk_Management.objects.filter(id = account.id).delete()
        return HttpResponse("Function Completed Successfully")        
    except Exception as e:
        exc_type, exe_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        logger_binance.error(exc_type,fname, exc_tb.tb_lineno, str(e))
        logger_binance.exception(str(e))



def daily_sl(request):
    accounts = Binance.objects.filter(risk_management =  True, is_disabled= False)
    if len(accounts) > 0:
        for binance in accounts:
            # check daily SL
            if binance.per_day_max_loss and binance.per_day_max_loss > 0:
                maxSL = binance.per_day_max_loss
                print("maxSL>>>>", maxSL)
                if binance.is_paper_account == True:
                    is_testnet = True
                else:
                    is_testnet = False
                client = Client(str(decrypt_keyids(binance.key_id)), str(decrypt_binance(binance.secret_id)), tld='com', testnet= is_testnet)
                summary = client.futures_account_balance(recvWindow = 5000000)
                summary= [item for item in summary if item.get('asset')=="USDT"]
                summary = summary[0]
                maxSLPercentage = (float(binance.daily_initial_balance) * float(binance.per_day_max_loss))/ 100
                print("maxSLPercentage>>>>", maxSLPercentage)
                maxSLValue = float(binance.daily_initial_balance)- maxSLPercentage
                print("maxSLVal>>>>", maxSLValue)
                currentVal = float (summary['balance'])
                print("currentVal>>>>", currentVal)
                if float(currentVal) <= float(maxSLValue):   
                    utils.close_open_order(client)
                    utils.close_all_positions(client)
                    
                    models.Binance.objects.filter(id = binance.id).update(is_disabled = True)
                    models.Binance_Risk_Management.objects.update_or_create(user_id=binance.id,risk_type = '2') 
                    models.Binance_Logs.objects.create(user_id = binance.id, message = "Daily Stop Loss Triggered")        
    return HttpResponse("Function Completed Successfully")    



def max_sl(request):
    accounts = Binance.objects.filter(risk_management =  True, is_disabled= False)
    if len(accounts) > 0:
        for binance in accounts:
            # check daily SL
            if binance.maximum_SL and binance.maximum_SL > 0:
                maxSL = binance.maximum_SL
                print("maxSL>>>>", maxSL)
                if binance.is_paper_account == True:
                    is_testnet = True
                else:
                    is_testnet = False
                if binance.intial_balance and float(binance.intial_balance)   > 0: 
                    init_bal = float(binance.intial_balance)
                else:
                    init_bal = 100000
                client = Client(str(decrypt_keyids(binance.key_id)), str(decrypt_binance(binance.secret_id)), tld='com', testnet= is_testnet)
                summary = client.futures_account_balance(recvWindow = 5000000)
                summary= [item for item in summary if item.get('asset')=="USDT"]
                summary = summary[0]
                maxSLPercentage = (init_bal * float(binance.per_day_max_loss))/ 100
                print("maxSLPercentage>>>>", maxSLPercentage)
                maxSLValue = float(init_bal)- maxSLPercentage
                print("maxSLVal>>>>", maxSLValue)
                currentVal = float (summary['balance'])
                print("currentVal>>>>", currentVal)
                if float(currentVal) <= float(maxSLValue):   
                    utils.close_open_order(client)
                    utils.close_all_positions(client)

                    models.Binance.objects.filter(id = binance.id).update(is_disabled = True)
                    models.Binance_Logs.objects.create(user_id = binance.id, message = "Max Stop Loss Triggered")            

    return HttpResponse("Function Completed Successfully")    
def show_order(request):
    binance = BinanceCommand.objects.all().order_by('-date_time')
    return render(request,'binance_show_order.html',{"context":binance})

def cancel_order_by_orderID(request,pk,order_id,symbol,clientorderid):
    try:
        response = cancel_active_order(binance=Binance.objects.get(pk=pk),orderId=order_id,symbol=symbol,origClientOrderId = clientorderid)
    except Exception as e:
        exc_type, exe_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        logger_binance.error(exc_type,fname, exc_tb.tb_lineno, str(e))
        logger_binance.exception(str(e))
    if response['status'] == "CANCELED":
        messages.success(request, f'Order ID {order_id} canceled Successfully.')
    else:
        messages.error(request, f'Order ID {order_id} not canceled.')
    return redirect('binances:binance_details', pk=pk)

def downloadCsv(request):  
    response = HttpResponse(content_type='text/csv')  
    response['Content-Disposition'] = 'attachment;filename="Binance_Logs.csv"'  
    logs = Binance_Logs.objects.all()  
    writer = csv.writer(response)  
    for log in logs:  
        writer.writerow([log.user,log.message,log.created_at]) 
    return response    

def download_server_logs(request):
    try:
        response = HttpResponse(open("binance_logs.log", 'rb').read())
        response['Content-Type'] = 'text/plain'
        response['Content-Disposition'] = 'attachment; filename=Binance_Server_Logs.csv'
        return response
    except Exception as e:
        exc_type, exe_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        logger_binance.error(exc_type,fname, exc_tb.tb_lineno, str(e))
        logger_binance.exception(str(e))