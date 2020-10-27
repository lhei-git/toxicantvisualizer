# This page handles requests by individual "view" functions
from django.http import HttpResponse, JsonResponse
from django.db.models import Q, Sum
from viewModule.models import Tri as tri
from viewModule.serializers import TriSerializer as t_szr
from django.core import serializers as szs
import json
import re

# SAMPLE coords-> ?ne_lat=13.3950&sw_lat=13.3948&sw_lng=144.7070&ne_lng=144.7072 {Yields 6 records in GUAM}

# Design Pattern - Use JsonResponse(...) for returning single item querysets or singular dictionary objects
#        Use HttpResponse(.., content_type=..) for returning querysets with multiple records

# Design Pattern - For selecting certain columns, specify in SERIALIZER(.., FIELDS=('...')) param.
#        and NOT IN ORM QUERY. If values() (and/or distinct()) is used in ORM query a <ValuesQuerySet>
#        is returned which is unusable by serializer, use json.dumps(list(..)) instead and return response


# facilities
def points(request):
    ne_lat = float(request.GET.get('ne_lat', default=0.0))
    ne_lng = float(request.GET.get('ne_lng', default=0.0))
    sw_lat = float(request.GET.get('sw_lat', default=0.0))
    sw_lng = float(request.GET.get('sw_lng', default=0.0))
    y = int(request.GET.get('year', default=2018))
    raw = tri.objects.filter(Q(latitude__lt=ne_lat) & Q(latitude__gt=sw_lat)
                                                    & Q(longitude__lt=ne_lng)
                                                    & Q(longitude__gt=sw_lng)
                                                    & Q(year=y))

    return HttpResponse(szs.serialize('json', raw), content_type='application/json')

def dist_fac(request):
    ne_lat = float(request.GET.get('ne_lat', default=0.0))
    ne_lng = float(request.GET.get('ne_lng', default=0.0))
    sw_lat = float(request.GET.get('sw_lat', default=0.0))
    sw_lng = float(request.GET.get('sw_lng', default=0.0))
    y = int(request.GET.get('year', default=2018))
    state = str(request.GET.get('state', default='None')).upper()
    if state != 'None' and ne_lat == 0.0 and sw_lng == 0.0 and ne_lng == 0.0 and sw_lat == 0.0:
        qs = tri.objects.filter(st=state, year=y).values('facilityname').distinct()
    else:
        qs = tri.objects.filter(Q(latitude__lt=ne_lat) & Q(latitude__gt=sw_lat)
                                                   & Q(longitude__lt=ne_lng)
                                                   & Q(longitude__gt=sw_lng)
                                                   & Q(year=y)).values('facilityname').distinct()
    #data = szs.serialize('json', qs) <--here values() is used so serializer will not work
    data = json.dumps(list(qs))
    return HttpResponse(data, content_type='application/json')

# stats/state/summary
def state_total_releases(request):
    state = str(request.GET.get('state')).upper()
    y = int(request.GET.get('year', default=2018))
    t_dioxin, t_carc, t_onsite, t_air, t_water, t_land, t_offsite, t_facilitycount = 0,0,0,0,0,0,0,0
    result = {}
    if state != 'None':
        t_facilitycount = int(tri.objects.filter(st=state, year=y).values('facility').distinct().count())
        tri_set = tri.objects.filter(st=state, year=y)
        for t in tri_set:
            if t.classification == 'Dioxin': # exclude dioxin stats in other categories
                t_dioxin += t.vet_total_releases
                if t.carcinogen == 'YES':
                    t_carc += t.vet_total_releases
            else:
                if t.carcinogen == 'YES': # carcinogens may be present in dioxins and non-dioxins
                    t_carc += t.vet_total_releases
                t_onsite += t.vet_total_releases_onsite
                t_offsite += t.vet_total_releases_offsite
                t_air += t.vet_total_releases_air
                t_water += t.total_releases_water
                t_land += t.vet_total_releases_land
        result = {'totalonsite':t_onsite, 'air':t_air, 'water':t_water, 'land':t_land,
                  'totaloffsite':t_offsite, 'totaldioxin':t_dioxin, 'totalcarcs':t_carc,
                  'numtrifacilities':t_facilitycount}
        return JsonResponse(result)

# FIXME - top_releases have repetitions, refer to err for distinct() here

# stats/location/parent_releases


def top_parentco_releases(request):
    ne_lat = float(request.GET.get('ne_lat', default=0.0))
    ne_lng = float(request.GET.get('ne_lng', default=0.0))
    sw_lat = float(request.GET.get('sw_lat', default=0.0))
    sw_lng = float(request.GET.get('sw_lng', default=0.0))
    y = int(request.GET.get('year', default=2018))
    state = str(request.GET.get('state', default='None')).upper()
    queryset = tri.objects.filter(Q(latitude__lt=ne_lat) & Q(latitude__gt=sw_lat)
                                  & Q(longitude__lt=ne_lng)
                                  & Q(longitude__gt=sw_lng)
                                  & Q(year=y) & ~Q(parent_co_name="NA")).values('parent_co_name').annotate(total=Sum('vet_total_releases_onsite')).annotate(land=Sum('vet_total_releases_land')).annotate(air=Sum('vet_total_releases_air')).annotate(water=Sum('total_releases_water')).order_by('-total')[:10]
    return JsonResponse(list(queryset), content_type='application/json', safe=False)

# stats/location/facility_releases


def top_facility_releases(request):
    ne_lat = float(request.GET.get('ne_lat', default=0.0))
    ne_lng = float(request.GET.get('ne_lng', default=0.0))
    sw_lat = float(request.GET.get('sw_lat', default=0.0))
    sw_lng = float(request.GET.get('sw_lng', default=0.0))
    y = int(request.GET.get('year', default=2018))
    state = str(request.GET.get('state', default='None')).upper()
    queryset = tri.objects.filter(Q(latitude__lt=ne_lat) & Q(latitude__gt=sw_lat)
                                  & Q(longitude__lt=ne_lng)
                                  & Q(longitude__gt=sw_lng)
                                  & Q(year=y)).values('facility').annotate(total=Sum('vet_total_releases_onsite')).annotate(land=Sum('vet_total_releases_land')).annotate(air=Sum('vet_total_releases_air')).annotate(water=Sum('total_releases_water')).order_by('-total')[:10]
    return JsonResponse(list(queryset), content_type='application/json', safe=False)

# stats/location/num_facilities
def num_facilities(request):
    state = str(request.GET.get('state')).upper()
    ne_lat = float(request.GET.get('ne_lat', default=0.0))
    ne_lng = float(request.GET.get('ne_lng', default=0.0))
    sw_lat = float(request.GET.get('sw_lat', default=0.0))
    sw_lng = float(request.GET.get('sw_lng', default=0.0))
    y = int(request.GET.get('year', default=2018))
    if state!='None' and ne_lat==0.0 and sw_lng==0.0 and ne_lng==0.0 and sw_lat==0.0:
        data = tri.objects.filter(st=state, year=y).values('facility').distinct().count()
    else:
        data = tri.objects.filter(Q(latitude__lt=ne_lat) & Q(latitude__gt=sw_lat)
                                  & Q(longitude__lt=ne_lng) & Q(longitude__gt=sw_lng)).values('facility')\
                                  .distinct().count()
    return HttpResponse(data, content_type='application/json')

# stats/location/summary
def location_summary(request):
    ne_lat = float(request.GET.get('ne_lat', default=0.0))
    ne_lng = float(request.GET.get('ne_lng', default=0.0))
    sw_lat = float(request.GET.get('sw_lat', default=0.0))
    sw_lng = float(request.GET.get('sw_lng', default=0.0))
    y = int(request.GET.get('year', default=2018))
    # FIXME - unit of measure can be filtered in ORM query below
    raw = tri.objects.filter(Q(latitude__lt=ne_lat) & Q(latitude__gt=sw_lat)
                                                    & Q(longitude__lt=ne_lng)
                                                    & Q(longitude__gt=sw_lng)
                                                    & Q(year=y))
    rows = list(map(lambda e: e.__dict__, list(raw)))
    summary = {}
    summary['num_facilities'] = len(set(list(map(lambda r: r['facility'], rows))))
    summary['num_distinct_chemicals'] = len(set(list(map(lambda r: clean_chemical_name(r['chemical']), rows))))
    summary['total_disposal'] = 0
    summary['total_on_site'] = 0
    summary['total_off_site'] = 0
    summary['total_air'] = 0
    summary['total_water'] = 0
    summary['total_land'] = 0
    summary['total_carcinogen'] = 0
    # TODO - make calculations based on unit of measure. Currently assumes everything is in pounds
    for r in rows: 
      summary['total_disposal'] += r['vet_total_releases']
      summary['total_on_site'] += r['vet_total_releases_onsite']
      summary['total_off_site'] += r['vet_total_releases_offsite']
      summary['total_air'] += r['vet_total_releases_air']
      summary['total_water'] += r['total_releases_water']
      summary['total_land'] += r['vet_total_releases_land']
      summary['total_carcinogen'] += r['vet_total_releases'] if r['carcinogen'] == 'YES' else 0
    response = json.dumps(summary)
    return HttpResponse(response, content_type='application/json')

def XXXlocation_releases_by_facility(request):
    ne_lat = float(request.GET.get('ne_lat', default=0.0))
    ne_lng = float(request.GET.get('ne_lng', default=0.0))
    sw_lat = float(request.GET.get('sw_lat', default=0.0))
    sw_lng = float(request.GET.get('sw_lng', default=0.0))
    y = int(request.GET.get('year', default=2018))
    state=str(request.GET.get('state', default='None'))
    raw = tri.objects.filter(Q(latitude__lt=ne_lat) & Q(latitude__gt=sw_lat)
                                                    & Q(longitude__lt=ne_lng)
                                                    & Q(longitude__gt=sw_lng)
                                                    & Q(year=y))
    rows = list(map(lambda e: e.__dict__, list(raw)))
    facilities = {}
    for r in rows:
      f = r['facilityname']
      if f in facilities:
          facilities[f] += r['vet_total_releases']
      else:
          facilities[f] = 0
    return HttpResponse(json.dumps(facilities), content_type='application/json')

def XXXlocation_releases_by_parent(request):
  ne_lat = float(request.GET.get('ne_lat', default=0.0))
  ne_lng = float(request.GET.get('ne_lng', default=0.0))
  sw_lat = float(request.GET.get('sw_lat', default=0.0))
  sw_lng = float(request.GET.get('sw_lng', default=0.0))
  y = int(request.GET.get('year', default=2018))
  state=str(request.GET.get('state', default='None'))
  raw = tri.objects.filter(Q(latitude__lt=ne_lat) & Q(latitude__gt=sw_lat)
                                                  & Q(longitude__lt=ne_lng)
                                                  & Q(longitude__gt=sw_lng)
                                                  & Q(year=y))
  rows = list(map(lambda e: e.__dict__, list(raw)))
  parents = {}
  for r in rows:
    f = r['parent_co_name']
    if f in parents:
        parents[f] += r['vet_total_releases']
    else:
        parents[f] = 0
  return HttpResponse(json.dumps(parents), content_type='application/json')

def chem_counts(request):
    ne_lat = float(request.GET.get('ne_lat', default=0.0))
    ne_lng = float(request.GET.get('ne_lng', default=0.0))
    sw_lat = float(request.GET.get('sw_lat', default=0.0))
    sw_lng = float(request.GET.get('sw_lng', default=0.0))
    y = int(request.GET.get('year', default=2018))
    raw = tri.objects.filter(Q(latitude__lt=ne_lat) & Q(latitude__gt=sw_lat)
                                                    & Q(longitude__lt=ne_lng)
                                                    & Q(longitude__gt=sw_lng)
                                                    & Q(year=y))
    rows = map(lambda e: e.__dict__, list(raw))
    top_chems = dict()
    for r in rows:
      chem = clean_chemical_name(r['chemical'])
      if not chem in top_chems:
        top_chems[chem] = 1
      else:
        top_chems[chem] = top_chems[chem] + 1
    return HttpResponse(json.dumps(top_chems), content_type='application/json')

def chem_amounts(request):
    ne_lat = float(request.GET.get('ne_lat', default=0.0))
    ne_lng = float(request.GET.get('ne_lng', default=0.0))
    sw_lat = float(request.GET.get('sw_lat', default=0.0))
    sw_lng = float(request.GET.get('sw_lng', default=0.0))
    y = int(request.GET.get('year', default=2018))
    raw = tri.objects.filter(Q(latitude__lt=ne_lat) & Q(latitude__gt=sw_lat)
                                                    & Q(longitude__lt=ne_lng)
                                                    & Q(longitude__gt=sw_lng)
                                                    & Q(year=y)).values('chemical').annotate(total=Sum('vet_total_releases')).order_by('-total')[:10]
    print(raw)
    return JsonResponse(list(raw), content_type='application/json', safe=False)

def XXXfac_count(request):
    state = str(request.GET.get('state')).upper()
    ne_lat = float(request.GET.get('ne_lat', default=0.0))
    ne_lng = float(request.GET.get('ne_lng', default=0.0))
    sw_lat = float(request.GET.get('sw_lat', default=0.0))
    sw_lng = float(request.GET.get('sw_lng', default=0.0))
    start = int(request.GET.get('start', default=2018))
    end = int(request.GET.get('end', default=2018))
    if state != 'None' and ne_lat==0.0 and sw_lng==0.0 and ne_lng==0.0 and sw_lat==0.0:
        count = tri.objects.filter(st=state).count()
        return HttpResponse(int(count), content_type='application/json')
    else:
        count = tri.objects.filter(Q(latitude__lt=ne_lat) & Q(latitude__gt=sw_lat)
                                   & Q(longitude__lt=ne_lng) & Q(longitude__gt=sw_lng)
                                   & Q(year__lte=end) & Q(year__gte=start)).count()
        return HttpResponse(int(count), content_type='application/json')

def clean_chemical_name(str):
  pattern = re.compile(r'\([^)]*\)|compounds|\"| and.*', re.IGNORECASE)
  return pattern.sub("", str).strip()

def attr(request, attribute=str()):
    attr = str(attribute).upper()
    if attr == 'ID':
        return idview(request)
    elif attr == 'CHEMICAL' or attr == 'CHEMICALS':
        return chemview(request)
    elif attr == 'CITY':
        return cityview(request)
    elif attr == 'ZIP':
        return zipview(request)

def idview(request):
    p_id = int(request.GET.get('id'))
    result = tri.objects.get(id=p_id)
    serializer = t_szr(result)
    return JsonResponse(serializer.data)

def chemview(request):
    p_chem = str(request.GET.get('chemical')).upper()
    resultset = tri.objects.filter(chemical=p_chem)[:10]
    return HttpResponse(szs.serialize('json', resultset), content_type='application/json')

def cityview(request):
    p_city = str(request.GET.get('city')).upper()
    resultset = tri.objects.filter(city=p_city)[:10]
    data = szs.serialize('json', resultset)
    return HttpResponse(data, content_type='application/json')

def zipview(request):
    p_zip = int(request.GET.get('zip'))
    resultset = tri.objects.filter(zip=p_zip)
    data = szs.serialize('json', resultset)
    return HttpResponse(data, content_type='application/json')

def demo(request, tri_attr=int(-9999)):
    if tri_attr == -9999:
        return HttpResponse('<h1>No attribute requested</h1>')
    else:
        return HttpResponse('<h1>TRI data for attribute # {}</h1>'.format(tri_attr))

# - https://docs.djangoproject.com/en/3.1/ref/models/querysets/#field-lookups
