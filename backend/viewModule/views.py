# This page handles requests by individual "view" functions
from django.http import HttpResponse, JsonResponse
from django.db.models import Q, Sum, Subquery
from viewModule.models import Tri as tri
from viewModule.models import Facility as facility
from viewModule.models import Chemical as chemical
from viewModule.models import Release as release
from viewModule.serializers import TriSerializer as t_szr
from django.core import serializers as szs
from django.core.serializers.json import DjangoJSONEncoder
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

""" 
Returns list of facilties filtered by geographic window, year, release type, and chemical classification.
"""
def get_facilities(request):
    ne_lat = float(request.GET.get('ne_lat', default=0.0))
    ne_lng = float(request.GET.get('ne_lng', default=0.0))
    sw_lat = float(request.GET.get('sw_lat', default=0.0))
    sw_lng = float(request.GET.get('sw_lng', default=0.0))
    carcinogen = request.GET.get('carcinogen')
    dioxin = request.GET.get('dioxin')
    pbt = request.GET.get('pbt')
    chemical = request.GET.get('chemical')
    release_type = request.GET.get('release_type')
    y = int(request.GET.get('year', default=2018))

    # filter by geographic window and year
    filters = (Q(latitude__lt=ne_lat) & Q(latitude__gt=sw_lat)
               & Q(longitude__lt=ne_lng)
               & Q(longitude__gt=sw_lng) & Q(release__year=y))

    # filter by release_type
    if release_type is not None:
        if release_type.lower() == 'air':
            filters &= Q(release__air__gt=0)
        elif release_type.lower() == 'water':
            filters &= Q(release__water__gt=0)
        elif release_type.lower() == 'land':
            filters &= Q(release__land__gt=0)
        elif release_type.lower() == 'on_site':
            filters &= Q(release__on_site__gt=0)
        elif release_type.lower() == 'off_site':
            filters &= Q(release__off_site__gt=0)

    # filter by chemicals
    if chemical is not None:
        filters &= Q(chemical__name=chemical)
               
    # filter by carcinogens, PBTs, or dioxins only
    if carcinogen is not None:
        filters &= Q(chemical__carcinogen='YES')
    elif dioxin is not None:
        filters &= Q(chemical__classification='Dioxin')
    elif pbt is not None:
        filters &= Q(chemical__classification='PBT')

    # add sum of total releases for the facility with these filters
    raw = facility.objects.filter(filters).annotate(
        total=Sum('release__total')).values()
    response = json.dumps(list(raw), cls=DjangoJSONEncoder)
    return HttpResponse(response, content_type='application/json')


def get_chemicals(request, facility_id):
    y = int(request.GET.get('year', default=2018))
    # raw = release.objects.filter(Q(facility_id=facility_id) & Q(year=y)).select_related('chemical').values()
    raw = chemical.objects.filter(facilities__id=facility_id, release__year=y).values().annotate(total=Sum('release__total'))
    response = json.dumps(list(raw), cls=DjangoJSONEncoder)
    return HttpResponse(response, content_type='application/json')

def dist_fac(request):
    ne_lat = float(request.GET.get('ne_lat', default=0.0))
    ne_lng = float(request.GET.get('ne_lng', default=0.0))
    sw_lat = float(request.GET.get('sw_lat', default=0.0))
    sw_lng = float(request.GET.get('sw_lng', default=0.0))
    y = int(request.GET.get('year', default=2018))
    state = str(request.GET.get('state', default='None')).upper()
    if state != 'None' and ne_lat == 0.0 and sw_lng == 0.0 and ne_lng == 0.0 and sw_lat == 0.0:
        qs = tri.objects.filter(st=state, year=y).values('facility').distinct()
    else:
        qs = tri.objects.filter(Q(latitude__lt=ne_lat) & Q(latitude__gt=sw_lat)
                                                   & Q(longitude__lt=ne_lng)
                                                   & Q(longitude__gt=sw_lng)
                                                   & Q(year=y)).values('facility').distinct()
    #data = szs.serialize('json', qs) <--here values() is used so serializer will not work
    data = json.dumps(list(qs))
    return HttpResponse(data, content_type='application/json')

'''
Return total stats released by state & year {graph }
'''
def state_total_releases(request):
    state = str(request.GET.get('state')).upper()
    y = int(request.GET.get('year', default=2018))
    t_dioxin, t_carc, t_onsite, t_air, t_water, t_land, t_offsite, t_facilitycount = 0,0,0,0,0,0,0,0
    result = {}
    filters = ()
    if state != 'None':



        '''
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
                  '''
        return JsonResponse(result)

# FIXME - replace raw queries with ORM calls

# stats/state/all
def all_state_total_releases(request):
    d = []
    y = int(request.GET.get('year', default=2018))
    results = tri.objects.raw(
        'SELECT max("t_ID") as "t_ID", st, sum(vet_total_releases_onsite) as totalonsite, sum(vet_total_releases) as total, sum(vet_total_releases_air) as air, sum(total_releases_water) as water, sum(vet_total_releases_land) as land, sum(vet_total_releases_offsite) as offsite, count(distinct(facility)) as facility FROM public."TRI_DATA" WHERE YEAR = ' + str(y) + ' GROUP BY st')
    for res in results:
        l = {"name": res.st, "totalonsite":res.totalonsite, "air": res.air, "water":res.water, "land":res.land, "totaloffsite":res.offsite, "numtrifacilities":res.facility, "total":res.total}
        d.append(l)
    return JsonResponse(list(d), safe=False)

# stats/county/all
def all_county_total_releases(request):
    d = []
    y = int(request.GET.get('year', default=2018))
    results = tri.objects.raw('SELECT max("t_ID") as "t_ID", st, county, sum(vet_total_releases_onsite) as totalonsite, sum(vet_total_releases) as total, sum(vet_total_releases_air) as air, sum(total_releases_water) as water, sum(vet_total_releases_land) as land, sum(vet_total_releases_offsite) as offsite, count(distinct(facility)) as facility FROM public."TRI_DATA" WHERE YEAR = ' + str(y) + ' GROUP BY st, county')
    for res in results:
        l = {"state": res.st, "county":res.county, "totalonsite":res.totalonsite, "air": res.air, "water":res.water, "land":res.land, "totaloffsite":res.offsite, "numtrifacilities":res.facility, "total":res.total}
        d.append(l)
    return JsonResponse(list(d), safe=False)

'''
Return top 10 companies in total releases by geo window & year
'''
def top_parentco_releases(request):
    ne_lat = float(request.GET.get('ne_lat', default=0.0))
    ne_lng = float(request.GET.get('ne_lng', default=0.0))
    sw_lat = float(request.GET.get('sw_lat', default=0.0))
    sw_lng = float(request.GET.get('sw_lng', default=0.0))
    y = int(request.GET.get('year', default=2018))
    
    f = (Q(facility__latitude__lt=ne_lat) & Q(facility__latitude__gt=sw_lat) & Q(facility__longitude__lt=ne_lng) 
                                     & Q(facility__longitude__gt=sw_lng) & Q(year=y))

    #queryset = release.objects.filter(f).order_by('-total').distinct('facility')
    # seems that the DISTINCT ON expression(s) must match the leftmost ORDER BY expression
    queryset = release.objects.filter(f).order_by('facility','-total').distinct('facility')
    '''
    queryset = tri.objects.filter(Q(latitude__lt=ne_lat) & Q(latitude__gt=sw_lat)
                                  & Q(longitude__lt=ne_lng)
                                  & Q(longitude__gt=sw_lng)
                                  & Q(year=y) & ~Q(parent_co_name="NA")).values('parent_co_name').annotate(total=Sum('vet_total_releases_onsite')).annotate(land=Sum('vet_total_releases_land')).annotate(air=Sum('vet_total_releases_air')).annotate(water=Sum('total_releases_water')).order_by('-total')[:10]
    '''
    #JsonResponse is breaking the return as it can't serialize the custom queryset (from cte)
    return HttpResponse(szs.serialize('json', queryset), content_type='application/json')

def timeline_top_parentco_releases(request):
    ne_lat = float(request.GET.get('ne_lat', default=0.0))
    ne_lng = float(request.GET.get('ne_lng', default=0.0))
    sw_lat = float(request.GET.get('sw_lat', default=0.0))
    sw_lng = float(request.GET.get('sw_lng', default=0.0))
    queryset = tri.objects.filter(Q(latitude__lt=ne_lat) & Q(latitude__gt=sw_lat)
                                  & Q(longitude__lt=ne_lng)
                                  & Q(longitude__gt=sw_lng)
                                  & Q(year=2018) & ~Q(parent_co_name="NA")).values('parent_co_name').annotate(total=Sum('vet_total_releases')).order_by('-total')[:10]

    response = {}
    response['years'] = [f['year'] for f in tri.objects.values("year").distinct("year").order_by("year")]
    for c in queryset:
      chem = c['parent_co_name']
      response[chem] = list(tri.objects.filter(Q(latitude__lt=ne_lat) & Q(
          latitude__gt=sw_lat) & Q(longitude__lt=ne_lng) & Q(longitude__gt=sw_lng) & Q(parent_co_name=chem)).values('year').annotate(total=Sum('vet_total_releases')))
    return HttpResponse(json.dumps(response), content_type='application/json')


def timeline_total(request):
    ne_lat = float(request.GET.get('ne_lat', default=0.0))
    ne_lng = float(request.GET.get('ne_lng', default=0.0))
    sw_lat = float(request.GET.get('sw_lat', default=0.0))
    sw_lng = float(request.GET.get('sw_lng', default=0.0))
    queryset = tri.objects.filter(Q(latitude__lt=ne_lat) & Q(latitude__gt=sw_lat)
                                  & Q(longitude__lt=ne_lng)
                                  & Q(longitude__gt=sw_lng)).values('year').annotate(total=Sum('vet_total_releases')).order_by('year')
    return JsonResponse(list(queryset), content_type='application/json', safe=False)

def top_facility_releases(request):
    ne_lat = float(request.GET.get('ne_lat', default=0.0))
    ne_lng = float(request.GET.get('ne_lng', default=0.0))
    sw_lat = float(request.GET.get('sw_lat', default=0.0))
    sw_lng = float(request.GET.get('sw_lng', default=0.0))
    y = int(request.GET.get('year', default=2018))
    state = str(request.GET.get('state', default='None')).upper()
    queryset = release.objects.select_related('facility').select_related('chemical').filter(Q(facility__latitude__lt=ne_lat) & Q(facility__latitude__gt=sw_lat)
                                  & Q(facility__longitude__lt=ne_lng)
                                  & Q(facility__longitude__gt=sw_lng)
                                  & Q(year=y)).values('facility__name').annotate(total=Sum('on_site')).annotate(land=Sum('land')).annotate(air=Sum('air')).annotate(water=Sum('water')).order_by('-total')[:10]
    return JsonResponse(list(queryset), content_type='application/json', safe=False)

def timeline_top_facility_releases(request):
    ne_lat = float(request.GET.get('ne_lat', default=0.0))
    ne_lng = float(request.GET.get('ne_lng', default=0.0))
    sw_lat = float(request.GET.get('sw_lat', default=0.0))
    sw_lng = float(request.GET.get('sw_lng', default=0.0))
    queryset = tri.objects.filter(Q(latitude__lt=ne_lat) & Q(latitude__gt=sw_lat)
                                  & Q(longitude__lt=ne_lng)
                                  & Q(longitude__gt=sw_lng)
                                  & Q(year=2018)).values('facility').annotate(total=Sum('vet_total_releases')).order_by('-total')[:10]

    response = {}
    response['years'] = [f['year'] for f in tri.objects.values("year").distinct("year").order_by("year")]
    for f in queryset:
      fac = f['facility']
      response[fac] = list(tri.objects.filter(Q(latitude__lt=ne_lat) & Q(
          latitude__gt=sw_lat) & Q(longitude__lt=ne_lng) & Q(longitude__gt=sw_lng) & Q(facility=fac)).values('year').annotate(total=Sum('vet_total_releases')))
    return HttpResponse(json.dumps(response), content_type='application/json')


# stats/location/num_facilities
def num_facilities(request):
    state = str(request.GET.get('state')).upper()
    ne_lat = float(request.GET.get('ne_lat', default=0.0))
    ne_lng = float(request.GET.get('ne_lng', default=0.0))
    sw_lat = float(request.GET.get('sw_lat', default=0.0))
    sw_lng = float(request.GET.get('sw_lng', default=0.0))
   # y = int(request.GET.get('year', default=2018))
    if state!='None' and ne_lat==0.0 and sw_lng==0.0 and ne_lng==0.0 and sw_lat==0.0:
        data = facility.objects.filter(st=state).values('name').distinct().count()
    else:
        data = facility.objects.filter(Q(latitude__lt=ne_lat) & Q(latitude__gt=sw_lat)
                                  & Q(longitude__lt=ne_lng) & Q(longitude__gt=sw_lng)).values('name')\
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
    raw = release.objects.select_related('facility').select_related('chemical').filter(Q(facility__latitude__lt=ne_lat),year=2018).values('facility__name', 'chemical__name', 'total', 'on_site', 'off_site', 'air', 'water', 'land', 'chemical__carcinogen')
    rows = list(map(lambda e: e.__dict__, list(raw)))
    summary = {}
    summary['num_facilities'] = len(set(list(map(lambda r: r['facility__name'], rows))))
    summary['num_distinct_chemicals'] = len(set(list(map(lambda r: clean_chemical_name(r['chemical__name']), rows))))
    summary['total_disposal'] = 0
    summary['total_on_site'] = 0
    summary['total_off_site'] = 0
    summary['total_air'] = 0
    summary['total_water'] = 0
    summary['total_land'] = 0
    summary['total_carcinogen'] = 0
    # TODO - make calculations based on unit of measure. Currently assumes everything is in pounds
    for r in rows:
      summary['total_disposal'] += r['total']
      summary['total_on_site'] += r['on_site']
      summary['total_off_site'] += r['off_site']
      summary['total_air'] += r['air']
      summary['total_water'] += r['water']
      summary['total_land'] += r['land']
      summary['total_carcinogen'] += r['total'] if r['chemical__carcinogen'] == 'YES' else 0
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
      f = r['facility']
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

# def chem_counts(request):
#     ne_lat = float(request.GET.get('ne_lat', default=0.0))
#     ne_lng = float(request.GET.get('ne_lng', default=0.0))
#     sw_lat = float(request.GET.get('sw_lat', default=0.0))
#     sw_lng = float(request.GET.get('sw_lng', default=0.0))
#     y = int(request.GET.get('year', default=2018))
#     raw = tri.objects.filter(Q(latitude__lt=ne_lat) & Q(latitude__gt=sw_lat)
#                                                     & Q(longitude__lt=ne_lng)
#                                                     & Q(longitude__gt=sw_lng)
#                                                     & Q(year=y))
#     rows = map(lambda e: e.__dict__, list(raw))
#     top_chems = dict()
#     for r in rows:
#       chem = clean_chemical_name(r['chemical'])
#       if not chem in top_chems:
#         top_chems[chem] = 1
#       else:
#         top_chems[chem] = top_chems[chem] + 1
#     return HttpResponse(json.dumps(top_chems), content_type='application/json')

def top_chemicals(request):
    ne_lat = float(request.GET.get('ne_lat', default=0.0))
    ne_lng = float(request.GET.get('ne_lng', default=0.0))
    sw_lat = float(request.GET.get('sw_lat', default=0.0))
    sw_lng = float(request.GET.get('sw_lng', default=0.0))
    y = int(request.GET.get('year', default=2018))
    raw = release.objects.select_related('facility').select_related('chemical').filter(Q(facility__latitude__lt=ne_lat) & Q(facility__latitude__gt=sw_lat)
                                                    & Q(facility__longitude__lt=ne_lng)
                                                    & Q(facility__longitude__gt=sw_lng)
                                                    & Q(year=y)).values('chemical__name').annotate(total=Sum('total')).order_by('-total')[:10]
    return JsonResponse(list(raw), content_type='application/json', safe=False)

def timeline_top_chemicals(request):
    ne_lat = float(request.GET.get('ne_lat', default=0.0))
    ne_lng = float(request.GET.get('ne_lng', default=0.0))
    sw_lat = float(request.GET.get('sw_lat', default=0.0))
    sw_lng = float(request.GET.get('sw_lng', default=0.0))
    queryset = tri.objects.filter(Q(latitude__lt=ne_lat) & Q(latitude__gt=sw_lat)
                                  & Q(longitude__lt=ne_lng)
                                  & Q(longitude__gt=sw_lng)
                                  & Q(year=2018)).values('chemical').annotate(total=Sum('vet_total_releases')).order_by('-total')[:10]

    response = {}
    response['years'] = [f['year'] for f in tri.objects.values("year").distinct("year").order_by("year")]
    for c in queryset:
      chem = c['chemical']
      response[chem] = list(tri.objects.filter(Q(latitude__lt=ne_lat) & Q(
          latitude__gt=sw_lat) & Q(longitude__lt=ne_lng) & Q(longitude__gt=sw_lng) & Q(chemical=chem)).values('year').annotate(total=Sum('vet_total_releases')))
    return HttpResponse(json.dumps(response), content_type='application/json')

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
