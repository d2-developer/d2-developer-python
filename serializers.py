import os
from rest_framework import serializers
from BINANCE.models import BinanceCommand, BinanceGroup, BinanceSymbol

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
secrets=""

class BinanceCommandSerializer(serializers.ModelSerializer):
    symbol = serializers.SlugRelatedField(queryset=BinanceSymbol.objects.all(),slug_field='symbol_id')

    class Meta:
        model = BinanceCommand
        fields = ['symbol','side','secret','group']
    def validate(self, data):
        """
        Check that secret matches secret and.
        """
        try:
            secret_key = BinanceGroup.objects.filter(secret_key=data['secret'],id = data['group'].id)
            if secret_key:
                return data
            else:
                raise serializers.ValidationError({"secret": "Authentication failed"})
        except Exception as e:
            raise serializers.ValidationError({"secret": "Authentication failed"})

    def create(self, validated_data):
        secret = validated_data.pop('secret')

        grp = validated_data.pop('group', None)
        
        if (grp.is_disabled):
            raise serializers.ValidationError({"group": "disabled"})
        data = BinanceCommand.objects.create(
            symbol=validated_data.pop('symbol'),
            side=validated_data.pop('side'),
            secret=secret,
            group=grp)
        return data
    
    def update(self, instance, validated_data):
        instance.save()
        return instance