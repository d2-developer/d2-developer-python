from django import forms
from django.core.exceptions import ValidationError
from BINANCE.models import Allocation, Binance, BinanceGroup, BinanceOrder, Currency, Customer, Plan, PlanMember, Position, Secret, Wallet,BinanceSymbol
from django.forms.widgets import CheckboxSelectMultiple, SelectMultiple

from BINANCE.order import place_order_binance
from .utils import *

SIDE = [
    ('buy','buy'),
    ('sell','sell'),]
CHOICES= [
    ('1', 'Equity use %'),
    ('2', 'Fixed Lot'),
    ('3', 'Amount In USD'),]

class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = '__all__'
        widgets = {'api_secret': forms.PasswordInput}

class BinanceFormEdit(forms.ModelForm):
    risk_management = forms.BooleanField(required=False)
    set_leverage = forms.BooleanField(required=False, label='Set Leverage')
    check_box = forms.BooleanField(required=False , label='Money Management')
    position = forms.ChoiceField(required=False,choices=CHOICES,label = '', widget=forms.RadioSelect())
    position_value = forms.FloatField(required=False ,label='Position Value')
    key_id = forms.CharField(max_length=100, required=True,label="Api Key *",widget=forms.TextInput(attrs={'placeholder': 'Api Key'}))
    secret_id = forms.CharField(max_length=100, required=True,label="Secret Key *",widget=forms.TextInput(attrs={'placeholder': 'Secret Key'}))
    binance_name = forms.CharField(max_length=100, required=True,label="Binance Account Name *",widget=forms.TextInput(attrs={'placeholder': 'Binance Account Name'}))
    intial_balance = forms.CharField(max_length=40,label='Intial Balance',)

    class Meta:
        model = Binance
        # fields = ['binance_name','key_id','secret_id','is_paper_account','free_money','limit_money','risk_management','per_trade_stop_loss','per_day_max_loss','maximum_SL','position','position_value']
        fields = ['binance_name','key_id','secret_id','is_paper_account','free_money','limit_money','risk_management','per_trade_stop_loss','per_day_max_loss','maximum_SL','position','position_value','set_leverage','leverage','comment','intial_balance']

    def __init__(self, *args, **kwargs):
        super(BinanceFormEdit, self).__init__(*args,**kwargs)
        self.instance.key_id = decrypt_keyids(self.instance.key_id)
        self.instance.secret_id = decrypt_binance(self.instance.secret_id)
        kwargs['instance'] = self.instance
        super(BinanceFormEdit, self).__init__(*args, **kwargs)
    
    def clean(self):
        cleaned_data = super().clean()
        position_value = cleaned_data.get('position_value')
        position = cleaned_data.get('position')
        if position and position_value == None:
            raise ValidationError("Position Value Mandatory fields")

class BinanceForm(forms.ModelForm):
    risk_management = forms.BooleanField(required=False)
    set_leverage = forms.BooleanField(required=False, label='Set Leverage')
    check_box = forms.BooleanField(required=False , label='Money Management')
    position = forms.ChoiceField(required=False,choices=CHOICES,label = '', widget=forms.RadioSelect())
    position_value = forms.FloatField(required=False ,label='Position Value')
    key_id = forms.CharField(max_length=100, required=True,label="Api Key *",widget=forms.TextInput(attrs={'placeholder': 'Api Key'}))
    secret_id = forms.CharField(max_length=100, required=True,label="Secret Key *",widget=forms.TextInput(attrs={'placeholder': 'Secret Key'}))
    binance_name = forms.CharField(max_length=100, required=True,label="Binance Account Name *",widget=forms.TextInput(attrs={'placeholder': 'Binance Account Name'}))
    intial_balance = forms.CharField(max_length=40,label='Intial Balance',)
    password = forms.PasswordInput()
    class Meta:
        model = Binance
        fields = ['binance_name','key_id','secret_id','is_paper_account','free_money','limit_money','risk_management','per_trade_stop_loss','per_day_max_loss','maximum_SL','position','position_value','set_leverage','leverage','comment','intial_balance']
        
    def clean(self):
        cleaned_data = super().clean()
        position_value = cleaned_data.get('position_value')
        position = cleaned_data.get('position')
        if position and position_value == None:
            raise ValidationError("Position Value Mandatory fields")
        
class Binance_GroupForm(forms.ModelForm):
    check_box = forms.BooleanField(required=False , label='Money Management')
    position = forms.ChoiceField(required=False,choices=CHOICES,label = '', widget=forms.RadioSelect())
    position_value = forms.FloatField(required=False ,label='Position Value')
    risk_management = forms.BooleanField(required=False)
    limit_money = forms.CharField(max_length=100, required=False)
    fixed_loss = forms.CharField(max_length=100, required=False)
    amount_in_usd = forms.CharField(max_length=100, required=False)
    name = forms.CharField(max_length=100, required=True,label="Group Name *",widget=forms.TextInput(attrs={'placeholder': 'Group Name','class': 'myfieldclass'}))

    class Meta:
        model = BinanceGroup
        fields = ['name','binance','stop_loss','inverse','per_trade_stop_loss','per_day_max_loss','maximum_SL','position_value','position','risk_management','same_side_direction']

    def __init__(self, *args, **kwargs):
        super(Binance_GroupForm, self).__init__(*args, **kwargs)
        self.fields["binance"].widget = SelectMultiple(attrs={'size': '12'})
        self.fields["binance"].queryset = Binance.objects.all()

class BinanceOrderForm(forms.ModelForm):
    symbol_str = forms.ModelChoiceField(queryset=BinanceSymbol.objects.all(),label='Symbol *')
    limit_value  = forms.CharField(max_length=100,required=False,label='')

    class Meta:
        model = BinanceOrder
        fields = ('symbol_str','quantity','side','order_type','duration','binance','created_by',)
        widgets = {'binance': forms.HiddenInput(),'created_by': forms.HiddenInput(),}

    # def clean_symbol_str(self):
    #     data = self.cleaned_data['symbol_str']
    #     return data.upper()

    def clean(self):
        cleaned_data = super().clean()
        binance = cleaned_data.get("binance")
        quantity = cleaned_data.get("quantity")
        side = cleaned_data.get("side")
        limit_value = cleaned_data.get("limit_value")
        print(">>>>>>>>>>>> limit value",limit_value)
        if quantity == None:
            raise ValidationError("Please Enter Quantity")
        if side == "---------":
            raise ValidationError("Please Select Side")
        response = place_order_binance(
            symbol_id=cleaned_data.get("symbol_str"),
            side=side,
            quantity= quantity,
            order_type=cleaned_data.get("order_type"),
            duration=cleaned_data.get("duration"),
            binance=binance,
            limit_price=limit_value,
            )


class PlanForm(forms.ModelForm):
    class Meta:
        model = Plan
        fields = '__all__'


class PlanParentForm(forms.ModelForm):
    class Meta:
        model = Plan
        fields = ['name']


class PlanMemberForm(forms.ModelForm):
    class Meta:
        model = PlanMember
        fields = '__all__'


class PlanMemberDetailForm(forms.ModelForm):
    class Meta:
        model = PlanMember
        fields = ['member_of','currency','percentage',]

class PositionForm(forms.ModelForm):
    
    def __init__(self, *args, **kwargs):
        super(PositionForm, self).__init__(*args, **kwargs)

    class Meta:
        model = Position
        fields = ('allocation','address','is_locked')
        
class BinanceReportForm(forms.Form):
    # symbol = forms.CharField(max_length=50,label='Symbol', required = False)
    symbol = forms.ModelChoiceField(queryset=BinanceSymbol.objects.all(),label='Symbol *')
    
    type = forms.CharField(max_length=50, required = False,label='Type')

class WalletForm(forms.ModelForm):
    class Meta:
        model = Wallet
        fields = '__all__'
        customer = forms.CharField(disabled=True)

class WalletDetailForm(forms.ModelForm):

    class Meta:
        model = Wallet
        fields = ('customer','broker','amount','max_position',)
        widgets = {'customer': forms.HiddenInput(),}


class SecretForm(forms.ModelForm):
    class Meta:
        model = Secret
        widgets = {'value': forms.PasswordInput(),}
        fields = ('container', 'key', 'value',)



class AllocationForm(forms.ModelForm):

    class Meta:
        model = Allocation
        fields = ('wallet','currency', 'allocated','positions_max',)

    def __init__(self, *args, **kwargs):
        super(AllocationForm, self).__init__(*args, **kwargs)
        self.fields['currency'].queryset = Currency.objects.get_coins()
        

class BinanceGroupOrderForm(forms.Form):

    symbol_str = forms.CharField(max_length=100,required=False,label='')
    side = forms.ChoiceField(choices=SIDE)
    price = forms.IntegerField()
    group = forms.ModelChoiceField(queryset=BinanceGroup.objects.all())
