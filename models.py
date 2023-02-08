import json
import os
from random import randint
from fernet_fields import EncryptedTextField
from django.db.models import Sum

from django.conf import settings
from django.db import models
from django.utils import timezone
from BINANCE.selector import CurrencyManager, binance_utility, coinbase_utility, select_binance_to_run_trade
from BINANCE.summary import get_binance_summary, get_open_order_position
from BINANCE.utils import binance_command_runner, decrypt_binance, decrypt_keyids
from BINANCE.wrapper import Wrapper, coercive_get_float
from django.core.validators import MaxValueValidator, MinValueValidator
from django.urls import reverse
# Create your models here.

SIDES = [
        ("buy", "buy"),
        ("sell", "sell"),
    ]

class BinanceGroup(models.Model):
    name = models.CharField(max_length=40,verbose_name='Group name',)
    binance = models.ManyToManyField(to='BINANCE.Binance')
    stop_loss = models.FloatField(default=20.0,validators=[MinValueValidator(0.0001),MaxValueValidator(25.0),],verbose_name='Stop Loss %')
    inverse = models.BooleanField(default=True)
    is_disabled = models.BooleanField(default=False)
    same_side_direction = models.BooleanField(default=False)
    position = models.IntegerField(verbose_name='Position',default="0")   # RADIO BUTTON VALUE
    position_value = models.FloatField(verbose_name='Position Value',blank=True,null=True)   # RADIO TEXT FIELD VALUE
    risk_management = models.BooleanField(default=False, verbose_name='risk management')
    per_trade_stop_loss = models.FloatField(validators=[MinValueValidator(0),MaxValueValidator(100)],blank=True,null=True)
    per_day_max_loss = models.FloatField(validators=[MinValueValidator(0),MaxValueValidator(100)],blank=True,null=True)
    maximum_SL  = models.FloatField(validators=[MinValueValidator(0),MaxValueValidator(100)],blank=True,null=True)
    secret_key = models.CharField(max_length=100, blank=True, null=True, default="secret")
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['name']
    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('binances:binance_groups_list')     

    def is_inverse(self):
        return self.inverse

    def id(self):
        return self.id

class Binance(models.Model):

    BROKER_NAMES = (
        ('Binance', 'Binance'),
        ('Coinbase', 'Coinbase'),
        ('Kraken', 'Kraken'),
        ('FTX', 'FTX'),
        ('Kucoin', 'Kucoin'),
        ('Nobroker', 'Nobroker'),)
    
    binance_name = models.CharField(max_length=40,blank=True,null=True,verbose_name='Account Name',)
    leverage = models.IntegerField(default=3,validators=[MinValueValidator(0),MaxValueValidator(100)],verbose_name='Leverage')
    key_id = models.CharField(max_length=200,default="ABC1234.001",)
    secret_id = models.CharField(max_length=200,default="123abcde-f1ab-abcd-e987-feee678beeff",)
    is_paper_account = models.BooleanField(default=False,verbose_name='Mark For Paper Trading',)
    free_money = models.FloatField(default=0.0,verbose_name='Free Money, US$',)
    limit_money = models.IntegerField(default=90,validators=[MinValueValidator(0),MaxValueValidator(100)],verbose_name='Limit Money, %',)
    asset_value = models.FloatField(default=0.0,verbose_name='Net Asset Value',blank=True,null=True,)
    last_updated = models.DateTimeField(auto_created=True,blank=True,null=True,)
    stop_loss = models.FloatField(default=20.0,validators=[MinValueValidator(0.0001),MaxValueValidator(25.0),],verbose_name='Stop Loss %')
    daily_stop_loss = models.FloatField(default=10.0,validators=[MinValueValidator(0.0001),MaxValueValidator(50.0),],verbose_name='Daily stop Loss %')
    daily_stop_loss_updated = models.DateTimeField(auto_created=True,blank=True,null=True,)
    is_disabled = models.BooleanField(default=False,verbose_name='Mark to stop trades',)
    summary = models.TextField(max_length=16000,verbose_name='Latest BINANCE account summary',blank=True,null=True,)
    risk_management = models.BooleanField(default=False, verbose_name='risk management')
    per_trade_stop_loss = models.FloatField(validators=[MinValueValidator(0),MaxValueValidator(100)],blank=True,null=True, verbose_name='Per Trade Stop Loss %')
    per_day_max_loss = models.FloatField(validators=[MinValueValidator(0),MaxValueValidator(100)],blank=True,null=True, verbose_name='Per Day Stop Loss %')
    maximum_SL  = models.FloatField(validators=[MinValueValidator(0),MaxValueValidator(100)],blank=True,null=True, verbose_name='Maximum SL Account Risk %')
    position = models.IntegerField(verbose_name='Position',default="0")   # RADIO BUTTON VALUE
    position_value = models.FloatField(verbose_name='Position Value',blank=True,null=True)   # RADIO TEXT FIELD VALUE
    comment = models.TextField(null=True,blank=True)
    enabled = models.BooleanField(default=False)
    leverage = models.IntegerField(default=3)
    broker_name = models.CharField(max_length=20,choices=BROKER_NAMES,help_text='Broker name',blank=True,null=True,)
    created_at = models.DateTimeField(auto_now_add=True)
    intial_balance = models.CharField(max_length=40,blank=True,null=True,verbose_name='intial_balance',)
    daily_initial_balance= models.FloatField(default="0", verbose_name='Daily Initial Balance' )
    daily_updated_at = models.DateTimeField(default=timezone.now, verbose_name='Daily Updated at')
    comment = models.TextField(null=True,blank=True,verbose_name='Comment')
    class Meta:
        ordering = ['binance_name']


    def decrypt_k_id(self):
        return str(decrypt_keyids(self.key_id))
    
    def decrypt_s_id(self):
        return str(decrypt_binance(self.secret_id))

    def __str__(self):
        return str(self.binance_name)

    def get_groups(self):
        groups = BinanceGroup.objects.filter(binance=self)
        return groups

    def get_absolute_url(self):

        return reverse('binances:binances_list')
    
    def get_balance(self):
        return Wrapper.get_balance(broker_name=self.broker_name,key_id=self.key_id,secret_id=self.secret_id)

    def make_order(self, coin=None, symbol=None, side=None):
        return Wrapper.make_order(
            broker_name=self.broker_name,
            key_id=self.key_id,secret_id=self.secret_id,leverage=self.leverage,is_paper_account=self.is_paper_account,symbol=symbol,side=side)
  
    def _update_summary(self):
        summary = get_binance_summary(self)
        if summary:
            self.summary = json.dumps(summary)
            self.last_updated = timezone.now()
            self.save()

    def _update_summary_by_timeout(self):
        if not self.last_updated:
            self._update_summary()
            return None
        else:
            seconds = (timezone.now() - self.last_updated).seconds
            min_s = settings.SUMMARY_UPDATE_MIN
            max_s = settings.SUMMARY_UPDATE_MAX
            random_timeout = randint(min_s, max_s)
            
            if seconds > random_timeout:
                self._update_summary()
        return None

    def _get_json_from_fresh_summary(self):

        self._update_summary_by_timeout()
        summary = {}
        if isinstance(self.summary, dict):
            summary = self.summary
        if isinstance(self.summary, str):
            summary = json.loads(self.summary)
        return summary

    def get_asset_value(self):

        summary = self._get_json_from_fresh_summary()
        asset_value = summary.get('totalMaintMargin', None)

        if asset_value:
            self.asset_value = asset_value
            self.save()
        return asset_value

    def get_free_money(self):

        summary = self._get_json_from_fresh_summary()
        
        return summary.get('totalWalletBalance', None)

    def get_positions(self):
        # get_open_order_position(self)
        positions = []
        summary = get_binance_summary(self)
        try:
            pos_str = summary.get('positions', None)

            if pos_str:
                for p in pos_str:

                    position = {}
                    position['symbolId'] = p.get('symbol')
                    position['entryPrice'] = coercive_get_float(p, 'entryPrice')
                    position['markPrice'] = coercive_get_float(p, 'markPrice',)
                    position['leverage'] = coercive_get_float(p, 'leverage')
                    position['positionAmt'] = coercive_get_float(p, 'positionAmt')
                    position['unRealizedProfit'] = coercive_get_float(p, 'unRealizedProfit')
                    positions.append(position)
            return positions
        except:
            return None
    
    def get_open_order(self):
        return get_open_order_position(self)
    
    # def active_orders(self):
    #     return get_active_orders(self)

    # def active_orders_symbol(self, symbol):
    #     return get_active_orders_symbol(self, symbol)    
    

class Binance_Risk_Management(models.Model):
    user = models.ForeignKey(Binance,on_delete=models.CASCADE,blank=True,null=True)
    stoped_at = models.DateTimeField(auto_now_add=True)
    type = models.CharField(max_length=10,blank=True,null=True,default="0")
    class Meta:
        verbose_name = 'Risk Management'


class BinanceCommandManager(models.Manager):
    def create(self, side, secret ,symbol=None,  group=None):
        if isinstance(symbol, str):
       
            symbol = BinanceSymbol.objects.filter(symbol=symbol).first()

        latest_order = BinanceCommand.objects.filter(group_id=group).filter(symbol_id=symbol).order_by('-id')
        
        if latest_order:
            
            latest_order = latest_order[0]
        else:
            latest_order = False    
        
        binance = select_binance_to_run_trade(Binance, group=group)
        save_command_res = binance_command_runner(binance, side, symbol, group=group , is_inverse= False) 
        
        command = BinanceCommand(symbol=symbol,side=side,secret=secret,group=group,)
        command.save()
        
        return command

class BinanceSymbol(models.Model):
    symbol_id = models.CharField(max_length=40,blank=True,null=True,help_text="AAPL.NASDAQ",)
    price = models.FloatField(default=0.001,blank=True,null=True,validators=[MinValueValidator(0.0001),],)
    weight = models.IntegerField(default=50,validators=[MinValueValidator(0),MaxValueValidator(100),],verbose_name='Amount % of ' 'allocated money to use')
    verified = models.BooleanField(default=True,)
    last_updated = models.DateTimeField(auto_created=True,blank=True,null=True,)
    ask_price = models.FloatField(default=0.001,validators=[MinValueValidator(0.0001),],)
    bid_price = models.FloatField(default=0.001,validators=[MinValueValidator(0.0001),],)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['symbol_id']
        verbose_name = 'Binance instrument'
    def __str__(self):
        return self.symbol_id

    def _update_prices(self):

        # bid, ask = get_symbol_last_feed(self.symbol_id)
        # if bid or ask:
        #     self.bid_price = bid
        #     self.ask_price = ask
        #     self.last_updated = timezone.now()
        #     self.save()

        return None

    def _update_prices_by_timeout(self):

        if not self.last_updated:
            self._update_prices()
            return None
        else:
            seconds = (timezone.now() - self.last_updated).seconds
            min_s = settings.SUMMARY_UPDATE_MIN
            max_s = settings.SUMMARY_UPDATE_MAX
            random_timeout = randint(min_s, max_s)
            
            if seconds > random_timeout:
                self._update_prices()
        return None

    def get_bid(self):
        self._update_prices_by_timeout()
        return self.bid_price

    def get_ask(self):
        self._update_prices_by_timeout()
        return self.ask_price


class BinanceCommand(models.Model):
    SIDES = [
        ("buy", "buy"),
        ("sell", "sell"),
    ]
    symbol = models.ForeignKey(BinanceSymbol,on_delete=models.CASCADE,blank=True,null=True,)
    side = models.CharField(max_length=8,choices=SIDES,)
    received = models.DateTimeField(auto_now_add=True,blank=True,null=True,)
    secret = models.CharField(max_length=200,blank=True,null=True,)
    group = models.ForeignKey(BinanceGroup,on_delete=models.CASCADE,blank=True,null=True,)   # pending change
    order_type = models.CharField(max_length=100,default="Market")
    date_time = models.DateTimeField(auto_now_add=True)
    objects = BinanceCommandManager()

    class Meta:
        ordering = ['received',]
    def __str__(self):
        return '{0}-{1}-{2}'.format(self.side,self.symbol,self.id)


class Binance_GroupOrder(models.Model):
    user =  models.ForeignKey(Binance,on_delete=models.CASCADE,blank=True,null=True)
    symbol = models.ForeignKey(BinanceSymbol,on_delete=models.CASCADE,blank=True,null=True, related_name="binance_symbols")
    order_id = models.CharField(max_length=100,blank=True,null=True)
    date_time = models.DateTimeField(auto_now_add=True)
    side = models.CharField(choices=SIDES,null=True,blank=True,max_length=20)
    
    class Meta:
        ordering = ['order_id' ]
    def __str__(self):
        return '{0}-{1}'.format(self.order_id,self.id)          

class Binance_Logs(models.Model):
    user = models.ForeignKey(Binance,on_delete=models.CASCADE,blank=True,null=True,related_name="binance_logs")
    message = models.CharField(max_length=5000,blank=True,null=True)
    status = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
class BinanceOrder(models.Model):

    SIDES = [
        ("buy", "Buy"),
        ("sell", "Sell"),
    ]

    ORDER_CHOICES = [
        'market',
        'limit', 
        # 'stop',
        # 'stop_limit',
       
    ]

    DURATION_CHOICES = ['day',]

    def make_choices_from_list(lst):
        return [(c, c.capitalize().replace('_', ' ')) for c in lst]

    symbol_str = models.CharField(max_length=40,blank=True,null=True,verbose_name='Symbol',)
    quantity = models.FloatField(blank=True,null=True)
    price = models.IntegerField(blank=True,null=True,)
    stop_price = models.IntegerField(blank=True,null=True,)
    side = models.CharField(max_length=40,choices=SIDES,blank=True,null=True,)
    order_type = models.CharField(max_length=40,choices=make_choices_from_list(ORDER_CHOICES),default=make_choices_from_list(ORDER_CHOICES)[0],blank=True,null=True,)
    duration = models.CharField(max_length=40,choices=make_choices_from_list(DURATION_CHOICES),default=make_choices_from_list(DURATION_CHOICES)[0],blank=True,null=True,)
    created = models.DateTimeField(auto_now=True,blank=True,null=True,)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    binance = models.ForeignKey(Binance,on_delete=models.CASCADE,blank=True,null=True,related_name='orders')
    details = models.TextField(max_length=4000)

    class Meta:
        ordering = ['created', ]

    def get_absolute_url(self):
        return reverse('binance:customers_flat_list')

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f'{self.side} {self.quantity} {self.symbol_str}'

class Plan(models.Model):
    name = models.CharField(max_length=200,blank=True,null=True,)
    
    def __str__(self):
        return '{} {}'.format(self.name,str(list(self.coins.all())))

    def get_absolute_url(self):
        return reverse('group_detail', args=[str(self.pk)])

class Customer(models.Model):
       
    BROKER_NAMES = (
        ('Binance', 'Binance'),
        ('Coinbase', 'Coinbase'),
        ('Kraken', 'Kraken'),
        ('FTX', 'FTX'),
        ('Kucoin', 'Kucoin'),
        ('Nobroker', 'Nobroker'),)
    name = models.CharField(max_length=40,default='New customer')
    comment = models.TextField(null=True,blank=True)
    api_key = models.CharField(max_length=200,null=True,blank=True)
    api_secret = EncryptedTextField(max_length=400,null=True,blank=True)
    enabled = models.BooleanField(default=False)
    is_paper = models.BooleanField(default=False,help_text='Enable paper trading')
    leverage = models.IntegerField(default=3)
    plan = models.ForeignKey(Plan,on_delete=models.CASCADE,null=True,blank=True,)
    broker_name = models.CharField(max_length=20,choices=BROKER_NAMES,help_text='Broker name',blank=True,null=True,)
    is_disabled = models.BooleanField(default=False,verbose_name='Mark to stop trades',)
    free_money = models.FloatField(default=0.0,verbose_name='Free money, US$',)
    limit_money = models.IntegerField(default=90,validators=[MinValueValidator(0),MaxValueValidator(100)],verbose_name='Limit money, %',)
    risk_management = models.BooleanField(default=False, verbose_name='risk management')
    per_trade_stop_loss = models.FloatField(validators=[MinValueValidator(0),MaxValueValidator(100)],blank=True,null=True, verbose_name='Per Trade Stop Loss %')
    per_day_max_loss = models.FloatField(validators=[MinValueValidator(0),MaxValueValidator(100)],blank=True,null=True, verbose_name='Per Day Stop Loss %')
    maximum_SL  = models.FloatField(validators=[MinValueValidator(0),MaxValueValidator(100)],blank=True,null=True, verbose_name='Maximum Stop Loss %')
    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name}"

    def get_balance(self):
        return Wrapper.get_balance(broker_name=self.broker_name,api_key=self.api_key,api_secret=self.api_secret,)
    
    def make_order(self, coin=None, symbol=None, side=None, ):
        return Wrapper.make_order(
            broker_name=self.broker_name,
            api_key=self.api_key,
            api_secret=self.api_secret,
            leverage=self.leverage,
            is_paper=self.is_paper,
            symbol=symbol,
            side=side,)

class Broker(models.Model):
    
    BROKER_NAMES = (
        ('Binance', 'Binance'),
        ('Coinbase', 'Coinbase'),
        ('Kraken', 'Kraken'),
        ('FTX', 'FTX'),
        ('Kucoin', 'Kucoin'),
        ('Nobroker', 'Nobroker'),)
    broker_name = models.CharField(max_length=20,choices=BROKER_NAMES,help_text='Broker name',blank=True,null=True,)

    class Meta:
        pass

    @staticmethod
    def test_get_broker_from_position(p):

        def get_utility_method(wallet):
            if wallet == 'Binance':
                return binance_utility
            elif wallet == 'Coinbase':
                return coinbase_utility
            else:
                raise NotImplemented

        wallet = p.allocation.wallet.broker

        utility = get_utility_method(wallet)

        test_message = utility()

        return {'wallet': wallet,'test_message': test_message,}




class Wallet(models.Model):
    
    customer = models.ForeignKey(Binance,on_delete=models.CASCADE,related_name='wallets',)
    broker = models.CharField(max_length=20,choices=Broker.BROKER_NAMES,help_text='Broker name',blank=True,null=True,)
    amount = models.FloatField(default=10000.0,verbose_name='Limit to use',)
    max_position = models.FloatField(default=0.75,validators=[MinValueValidator(0.0),MaxValueValidator(1.0)],verbose_name='Part of limit can be traded')
    enabled = models.BooleanField(default=False,)
    class Meta:
        ordering = ['customer','broker',]
        constraints = [models.UniqueConstraint(fields=['customer','broker', ],name='Only wallet per broker'),]
        verbose_name = 'Customer\'s wallet for Broker'
        verbose_name_plural = 'Customers\' wallets'

    def __str__(self):
        if self.customer.binance_name == None or self.broker == None:
            return 'Customer Name ' + 'OR' + ' Broker Name is Not Available'
        else:
            return self.customer.binance_name + '-' + self.broker

class Secret(models.Model):

    KEY_NAMES = (
        ('api_key', 'api_key'),
        ('api_secret', 'api_secret'),
        ('api_token', 'api_token'),
    )

    container = models.ForeignKey(Wallet,on_delete=models.CASCADE,related_name='secrets',)
    key = models.CharField(choices=KEY_NAMES,max_length=500,db_index=True)
    value = models.CharField(max_length=40,db_index=True,)
    
    def __str__(self):
        return self.container.broker + ' ' + self.key


class Currency(models.Model):
    symbol = models.CharField(max_length=200)   
    is_stable = models.BooleanField(default=False)
    description = models.CharField(max_length=200)
    to_usdt = models.FloatField(null=True,blank=True,)
    updated = models.DateTimeField(auto_now=True,)
    objects = CurrencyManager()
    class Meta:
        ordering = ['symbol']
        verbose_name_plural = "currencies"
        constraints = [models.UniqueConstraint(fields=['symbol'],name='unique symbol')]

    def __str__(self):
        return self.symbol
    
class Allocation(models.Model):

    wallet = models.ForeignKey(Wallet,null=True,blank=True,on_delete=models.CASCADE,)
    currency = models.ForeignKey(Currency,null=True,blank=True,on_delete=models.CASCADE,)
    allocated = models.FloatField(null=True,blank=True,validators=[MinValueValidator(0.0),MaxValueValidator(1.0)],verbose_name='Part allocated for trade in this currency',)
    positions_max = models.PositiveIntegerField(verbose_name='Max positions can be opened at time',default=3,)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['wallet', 'currency', ],name='One currency allocation per wallet')]

    def __str__(self):
        return f'{self.wallet} {self.currency}'



class PlanMember(models.Model):
    member_of = models.ForeignKey(Plan,on_delete=models.CASCADE,related_name='coins',)
    currency = models.ForeignKey(Currency,on_delete=models.CASCADE,related_name='members',)
    percentage = models.IntegerField(validators=[MinValueValidator(1),MaxValueValidator(100)],)

    def __str__(self):
        return '{}@{}'.format(self.percentage,self.currency)


def check_percentage_less_100(o):
    
    sub_total = Allocation.objects.filter(exchange=o.exchange).aggregate(Sum('allocated')).get('allocated__sum', 0)

    if not o.pk:
        return (sub_total + o.allocated) <= 1.0

    else:
        prev_obj = Allocation.objects.get(pk=o.pk)

        prev = prev_obj.allocated

        return (sub_total + o.allocated - prev) <= 1.0

    
class Position(models.Model):
    allocation = models.ForeignKey(Allocation,on_delete=models.CASCADE,related_name='positions',null=True,blank=True,)
    address = models.SmallIntegerField(verbose_name='Address in sequence of trade',)
    is_locked = models.BooleanField(default=False,)
    updated = models.DateTimeField(verbose_name='Time position was updated',auto_now=True,null=True,blank=True,)
    price = models.FloatField(verbose_name='Coin price when position was updated',null=True,blank=True,)
    objects = models.Manager()

    class Meta:
        constraints = [models.UniqueConstraint(fields=['allocation', 'address'],name='Unique address in the trade sequence of the coin allocation')]
        verbose_name = 'Certain position in the trading'
        verbose_name_plural = 'Positions for trading'
        ordering = ['allocation', 'address']

    def __str__(self):
        state_verb = 'locked' if self.is_locked else 'open'
        return f'{self.allocation}:{self.address} {state_verb}'

class Pool(models.Model):
    pass