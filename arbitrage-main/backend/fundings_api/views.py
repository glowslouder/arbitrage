# from django.shortcuts import render
from .models import MainFundingModel
from django.http import JsonResponse
from json import loads

# Create your views here.
def getFundingsView(request):
    if request.method == "OPTIONS":
        response = JsonResponse({})
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type, ngrok-skip-browser-warning"
        return response
    
    data = MainFundingModel.objects.all().order_by('-time').first()
    return_data = {
        'time': data.time,
        'coins': [

        ]
    }
    for coin in data['fundings']:
        if len(data['fundings'][coin]) > 1:
            keys = data['fundings'][coin].keys()
            max_ = ['', -100000]
            min_ = ['', 100000]
            for i in keys:
                if data['fundings'][coin][i]['index_price'] == 0:
                    continue
                if data['fundings'][coin][i]['rate'] > max_[1]:
                    max_ = [i, data['fundings'][coin][i]['rate'], data['fundings'][coin][i]['index_price'], data['fundings'][coin][i]['reset_time']]
                if data['fundings'][coin][i]['rate'] < min_[1]:
                    min_ = [i, data['fundings'][coin][i]['rate'], data['fundings'][coin][i]['index_price'], data['fundings'][coin][i]['reset_time']]
            return_data['coins'].append(
                {
                    'coin': coin,
                    'max': {
                        'exchange': max_[0],
                        'rate': max_[1],
                        'index_price': max_[2],
                        'reset_time': max_[3]
                    },
                    'min': {
                        'exchange': min_[0],
                        'rate': min_[1],
                        'index_price': min_[2],
                        'reset_time': min_[3]
                    },
                    'delta': max_[1] - min_[1],
                    'APR': (max_[1] - min_[1])*24*365,
                    'spread': abs(max_[2]-min_[2])/max(max_[2], min_[2])*100 if max(max_[2], min_[2]) else -1
                }
            )
    return_data['coins'].sort(key=lambda x: x['delta'], reverse=True)
    return JsonResponse(return_data, safe=False)