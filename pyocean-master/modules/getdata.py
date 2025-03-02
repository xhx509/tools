import csv
from matplotlib.dates import date2num, num2date
import datetime as dt
import scipy
import pylab
import sys
import time
import matplotlib.pyplot as plt
import matplotlib.mlab as ml
import numpy as np
from conversions import distance,dm2dd,fth2m
from pydap.client import open_url
import pandas as pd # needed for new ERDDAP data extractions
from dateutil.parser import parse
import pytz
#from basemap import basemap_usgs


def get_dataset(url):
    try:
        dataset = open_url(url)
    except:
        print 'Sorry, ' + url + 'is not available' 
        sys.exit(0)
    return dataset


def getdrift_header():
    # simple function that returns all ids in the drift_header table
    url = 'http://gisweb.wh.whoi.edu:8080/dods/whoi/drift_header'
    dataset = get_dataset(url)
    id=map(int,dataset.drift_header.ID)
    return id

def getdrift_ids():
    # simple function that returns all distinct ids in the drift_data table
    # this takes a few minutes and is limited to 300000 until the server is
    # restarted to pick up a 100000 "JDBCMaxResponseLength in web_sv.xml
    url = 'http://gisweb.wh.whoi.edu:8080/dods/whoi/drift_data'
    dataset = get_dataset(url)
    print 'Note: It takes a minute or so to determine distinct ids'
    ids=list(set(list(dataset.drift_data.ID)))
    return ids
    
def getdrift(did):
    """
    uses pandas to get remotely-stored drifter data via ERDDAP given a deployment id ("did") number
    where "did" is a string representing a deployment id.
    """
    url = 'http://comet.nefsc.noaa.gov:8080/erddap/tabledap/drifters.csv?time,latitude,longitude,depth&id="'+did+'"'
    print url
    df=pd.read_csv(url,skiprows=[1])
    # generate this datetime 
    for k in range(len(df)):
       df.time[k]=parse(df.time[k])
    #df=df.sort(df['time'].values)
    lat=df.latitude.values
    lon=df.longitude.values
    depth=df.depth.values
    time=df.time.values
    print 'Sorting mooring data by time'
    index = range(len(time))
    index.sort(lambda x, y:cmp(time[x], time[y]))
    #reorder the list of date_time,u,v
    time= [time[i] for i in index]
    lat = [lat[i] for i in index]
    lon = [lon[i] for i in index]
    depth = [depth[i] for i in index]
    return time,lat,lon,depth

def getcodar(url, datetime_wanted):
    """
    Routine to track particles very crudely though the codar fields
    by extracting data from their respective OPeNDAP/THREDDS archives via the pyDAP method
    Example input: 
    datetime_wanted = datetime.datetime(2007,10,2)                     
    url = "http://tashtego.marine.rutgers.edu:8080/thredds/dodsC/cool/codar/totals/sw06"
    """
    print datetime_wanted                
    
    dtime = open_url(url + '?time')
    id = ml.find(np.array(dtime['time']) == date2num(datetime_wanted) - date2num(dt.datetime(2001, 1, 1, 0, 0)))
    
    dataset = open_url(url + '?u[' + str(int(id)) + '],v[' + str(int(id)) + '],lat,lon,time[' + str(int(id)) + ']')
    print url + '?u[' + str(int(id)) + '],v[' + str(int(id)) + '],lat,lon,time[' + str(int(id)) + ']'   
    
    lat_array = dataset['lat']
    lon_array = dataset['lon']
    u1 = dataset['u']
    v1 = dataset['v']
    print lat_array
    u, v = [], []
    
    lat_vel = [lat for lat in lat_array]
    lon_vel = [lon for lon in lon_array] 
    
    [lon_vel, lat_vel] = pylab.squeeze(list(np.meshgrid(lon_vel, lat_vel)))   
    
    u1 = pylab.squeeze(list(np.array(u1.u[id])))
    v1 = pylab.squeeze(list(np.array(v1.v[id])))

    for y in range(len(u1)): 
        u.append(u1[y] / 100)    # converting to m/s
        v.append(v1[y] / 100)
        
    return lat_vel, lon_vel, u, v



def getcodar1(url, starttime, endtime):
    """
    returns all the velocity fields
    """
    try:          
        dataset = open_url(url + '?time')
        print dataset
    except:
        print 'Sorry, ' + url + ' not available' 
        sys.exit(0)

    jdmat_1 = dt.datetime(dataset) #units: days since 2001-01-01 00:00:00
    
    print jdmat_1
    lat_array = dataset['lat']
    lon_array = dataset['lon']
    u1 = dataset['u']
    v1 = dataset['v']
    #change array to list: lat & lon
    jdmat_m, u, v = [], [], []
    
    lat_vel = [lat for lat in lat_array]
    lon_vel = [lon for lon in lon_array] 
    lon_vel = np.array(lon_vel)
    lat_vel = np.array(lat_vel)
    
    lon_vel = lon_vel.reshape(np.size(lon_vel))
    lat_vel = lat_vel.reshape(np.size(lat_vel))

    jdmat_2 = [j for j in jdmat_1] 
        
    id = list(np.where(jdmat_2 > np.array(jdmat_2[-1] - 20))[0])
    for i in id:
        u.append(u1[i] / 100)# converting to m/s
        v.append(v1[i] / 100)
        jdmat_m.append(jdmat_1[i])
    print jdmat_m[0], len(jdmat_m), len(u[0]), len(lat_vel), len(lon_vel)
    return jdmat_m, lat_vel, lon_vel, u, v

def getemolt_latlon(site):
    """
    get lat, lon, and depth for a particular emolt site 
    """
    #urllatlon = 'http://gisweb.wh.whoi.edu:8080/dods/whoi/emolt_site?emolt_site.SITE,emolt_site.LAT_DDMM,emolt_site.LON_DDMM,emolt_site.ORIGINAL_NAME,emolt_site.BTM_DEPTH&emolt_site.SITE='
    urllatlon = 'http://comet.nefsc.noaa.gov:8080/erddap/tabledap/eMOLT.csv?latitude,longitude,depth&SITE="'+str(site)+'"&distinct()'
    df=pd.read_csv(urllatlon,skiprows=[1])
    return df.latitude[0], df.longitude[0], df.depth[0]


def getemolt_uv(site, input_time, dep):
    """
    get data from url, return datetime, u, v, depth
    input_time can either contain two values: start_time & end_time OR one value:interval_days
    """
    url = 'http://gisweb.wh.whoi.edu:8080/dods/whoi/emolt_sensor?emolt_sensor.SITE,emolt_sensor.YRDAY0_LOCAL,emolt_sensor.TIME_LOCAL,emolt_sensor.TEMP,emolt_sensor.DEPTH_I,emolt_sensor.U,emolt_sensor.V&emolt_sensor.SITE='
    # get the emolt_sensor data
    dataset = get_dataset(url + '"' + site + '"')
    var = dataset['emolt_sensor']
    print 'Making lists of mooring data'
    u = list(var.U)
    v = list(var.V)
    depth = list(var.DEPTH_I)
    time0 = list(var.YRDAY0_LOCAL)
    year_month_day = list(var.TIME_LOCAL)
  
    print 'Generating a datetime for mooring data'
    date_time, date_time_time = [], []
    for i in scipy.arange(len(time0)):
        date_time_time.append(num2date(time0[i]).replace(year=time.strptime(year_month_day[i], '%Y-%m-%d').tm_year).replace(day=time.strptime(year_month_day[i], '%Y-%m-%d').tm_mday))
        date_time.append(date2num(date_time_time[i]))#+float(4)/24) # makes it UTC
 
    #get the index of sorted date_time
    print 'Sorting mooring data by time'
    index = range(len(date_time))
    index.sort(lambda x, y:cmp(date_time[x], date_time[y]))
    #reorder the list of date_time,u,v
    date_time_num = [date_time[i] for i in index]
    u = [u[i] for i in index]
    v = [v[i] for i in index]
    depth = [depth[i] for i in index]

    print 'Delimiting mooring data according to user-specified time'  
    part_v, part_u, part_time = [], [], []
    if len(input_time) == 2:
        start_time = input_time[0]
        end_time = input_time[1]
    if len(input_time) == 1:
        start_time = date_time_num[0]
        end_time = start_time + input_time[0]
    print date_time_num[0], date_time_num[-1]
    for i in range(0, len(u)):
        if (start_time <= date_time_num[i] <= end_time) & (depth[i] == dep):
            part_v.append(v[i] / 100)
            part_u.append(u[i] / 100)
            part_time.append(num2date(date_time_num[i]))

    u = part_u
    v = part_v
    
    return part_time, u, v, depth, start_time, end_time

def getemolt_temp(site, input_time=[dt.datetime(1880,1,1),dt.datetime(2020,1,1)], dep=[0,1000]):
    """
    get data from url, return datetime, temperature, and start and end times
    input_time can either contain two values: start_time & end_time OR one value:interval_days
    """
    url = 'http://gisweb.wh.whoi.edu:8080/dods/whoi/emolt_sensor?emolt_sensor.SITE,emolt_sensor.YRDAY0_LOCAL,emolt_sensor.TIME_LOCAL,emolt_sensor.TEMP,emolt_sensor.DEPTH_I&emolt_sensor.SITE='
    # get the emolt_sensor data
    dataset = get_dataset(url + '"' + site + '"')
    var = dataset['emolt_sensor']
    print 'extracting eMOLT data using PyDap... hold on'
    temp = list(var.TEMP)
    depth = list(var.DEPTH_I)
    time0 = list(var.YRDAY0_LOCAL)
    year_month_day = list(var.TIME_LOCAL)
  
    print 'Generating a datetime ... hold on'
    datet = []
    for i in scipy.arange(len(time0)):
        #datet.append(num2date(time0[i]+1.0).replace(year=time.strptime(year_month_day[i], '%Y-%m-%d').tm_year).replace(day=time.strptime(year_month_day[i], '%Y-%m-%d').tm_mday))
        datet.append(num2date(time0[i]+1.0).replace(year=dt.datetime.strptime(year_month_day[i], '%Y-%m-%d').year).replace(month=dt.datetime.strptime(year_month_day[i],'%Y-%m-%d').month).replace(day=dt.datetime.strptime(year_month_day[i],'%Y-%m-%d').day).replace(tzinfo=None))
    #get the index of sorted date_time
    print 'Sorting mooring data by time'
    index = range(len(datet))
    index.sort(lambda x, y:cmp(datet[x], datet[y]))
    #reorder the list of date_time,u,v
    datet = [datet[i] for i in index]
    temp = [temp[i] for i in index]
    depth = [depth[i] for i in index]

    print 'Delimiting mooring data according to user-specified time'  
    part_t,part_time = [], []
    if len(input_time) == 2:
        start_time = input_time[0]
        end_time = input_time[1]
    if len(input_time) == 1:
        start_time = datet[0]
        end_time = start_time + input_time[0]
    if  len(input_time) == 0:
        start_time = datet[0]
        end_time=datet[-1]
    print datet[0], datet[-1]
    for i in range(0, len(temp)):
        if (start_time <= datet[i] <= end_time) & (dep[0]<=depth[i]<= dep[1]):
            part_t.append(temp[i])
            part_time.append(datet[i])        
    temp=part_t
    datet=part_time
    
    return datet,temp

def getobs_tempsalt_bysite(site,input_time):
    """
Function written by Jim Manning and used in "modvsobs" and "getemolt",it was modified by Huanxin
get data from url, return depth temperature,latitude,longitude, and start and end times
input_time can either contain two values: start_time & end_time OR one value:interval_days
and they should be timezone aware
example: input_time=[dt(2003,1,1,0,0,0,0,pytz.UTC),dt(2009,1,1,0,0,0,0,pytz.UTC)]
"""
    mintime=input_time[0].strftime('%Y-%m-%d'+'T'+'%H:%M:%S'+'Z')  # change time format
    maxtime=input_time[1].strftime('%Y-%m-%d'+'T'+'%H:%M:%S'+'Z')    
   
    url='http://comet.nefsc.noaa.gov:8080/erddap/tabledap/eMOLT.csv?SITE,time,depth,sea_water_temperature,latitude,longitude&time>='\
    +str(mintime)+'&time<='+str(maxtime)+'&SITE="'+str(site)+'"&orderBy("depth,time")'
    df=pd.read_csv(url,skiprows=[1])
    for k in range(len(df)):
       df.time[k]=parse(df.time[k])

    return df.time.values,df.sea_water_temperature.values,df.depth.values,df.SITE.values,df.latitude.values,df.longitude.values

def getobs_tempsalt_byrange(gbox,depth,input_time):
    """
Function written by Huanxin and used in "getemolt"
get data from url, return depth temperature,latitude,longitude, and start and end times
gbox includes 4 values, maxlon, minlon,maxlat,minlat, example:  [-69.0,-73.0,41.0,40.82]
depth includes bottom depth and surface depth,example:  [80,0]
input_time can either contain two values: start_time & end_time OR one value:interval_days
and they should be timezone aware
example: input_time=[dt(2003,1,1,0,0,0,0,pytz.UTC),dt(2009,1,1,0,0,0,0,pytz.UTC)]
"""
    i_maxdepth=depth[0];i_mindepth=depth[1];lon_max=gbox[0];lon_min=gbox[1];lat_max=gbox[2];lat_min=gbox[3]
    mintime=input_time[0].strftime('%Y-%m-%d'+'T'+'%H:%M:%S'+'Z')  # change time format
    maxtime=input_time[1].strftime('%Y-%m-%d'+'T'+'%H:%M:%S'+'Z')
    url='http://comet.nefsc.noaa.gov:8080/erddap/tabledap/eMOLT.csv?SITE,time,depth,sea_water_temperature,latitude,longitude&time>='\
    +str(mintime)+'&time<='+str(maxtime)+'&depth<='+str(i_maxdepth)+'&depth>='+str(i_mindepth)+'&latitude>='\
    +str(lat_min)+'&latitude<='+str(lat_max)+'&longitude>='+str(lon_min)+'&longitude<='+str(lon_max)+'&orderBy("SITE,depth,time")'
    df=pd.read_csv(url,skiprows=[1])
    for k in range(len(df)):
       df.time[k]=parse(df.time[k])
    return df.time.values,df.sea_water_temperature.values,df.depth.values,df.SITE.values,df.latitude.values,df.longitude.values
    


  
#def get_w_depth(xi, yi, url='http://geoport.whoi.edu/thredds/dodsC/bathy/gom03_v03'):
def get_w_depth(xi,yi):
    url='http://geoport.whoi.edu/thredds/dodsC/bathy/gom03_v1_0'#url='http://geoport.whoi.edu/thredds/dodsC/bathy/crm_vol1.nc' ):
    if xi[0]>999.: # if it comes in decimal -minutes, conert it
        #for kk in range(len(xi)):
        (y2,x2)=dm2dd(yi[0],xi[0])
        yi[0]=y2
        xi[0]=x2
    try:    
        dataset = open_url(url)
        
    except:
        print 'Sorry, ' + url + ' is not available' 
        sys.exit(0)

    #read lat, lon,topo from url
    xgom_array = dataset['lon']
    ygom_array = dataset['lat']
    dgom_array = dataset['topo'].topo

    #print dgom_array.shape, xgom_array[5:9],dgom_array[5]

    #convert the array to a list
    xgom, ygom = [], []
    
    for i in xgom_array:
        if i > xi[0] - 0.00834 and i < xi[0] + 0.00834:
            xgom.append(i)
  
    for i  in ygom_array:
        if i > yi[0] - 0.00834 and i < yi[0] + 0.00834:
            ygom.append(i)


    x_index, y_index = [], []
    (ys, xs) = dgom_array.shape

    for i in range(0, len(xgom)):
        x_index.append(int(round(np.interp(xgom[i], xgom_array, range(xs)))))
    for i in range(0, len(ygom)):
        y_index.append(int(round(np.interp(ygom[i], ygom_array, range(ys)))))
    
    dep, distkm, dist1 = [], [], []

    for k in range(len(x_index)):
        for j in range(len(y_index)):
            dep.append(dgom_array[(y_index[j], x_index[k])])
       
            distkm, b = distance((ygom[j], xgom[k]), (yi[0], xi[0]))
            dist1.append(distkm)
    #print dist1        
    if len(dist1)>=3:    
      #get the nearest,second nearest,third nearest point.
      dist_f_nearest = sorted(dist1)[0]
      dist_s_nearest = sorted(dist1)[1]
      dist_t_nearest = sorted(dist1)[2]
    
      index_dist_nearest = range(len(dist1))
      index_dist_nearest.sort(lambda x, y:cmp(dist1[x], dist1[y]))
    
      dep_f_nearest = dep[index_dist_nearest[0]]
      dep_s_nearest = dep[index_dist_nearest[1]]
      dep_t_nearest = dep[index_dist_nearest[2]]

      #compute the finally depth
      d1 = dist_f_nearest
      d2 = dist_s_nearest
      d3 = dist_t_nearest
      def1 = dep_f_nearest
      def2 = dep_s_nearest
      def3 = dep_t_nearest
      depth_finally = def1 * d2 * d3 / (d1 * d2 + d2 * d3 + d1 * d3) + def2 * d1 * d3 / (d1 * d2 + d2 * d3 + d1 * d3) + def3 * d2 * d1 / (d1 * d2 + d2 * d3 + d1 * d3)
    else:
      depth_finally = -999  
    return depth_finally

def getgomoos(site, *days):
    """
    Input: one value - interval days OR two values - start_time and end time
    """
    time_add_num = date2num(dt.datetime(1858, 11, 17))
    url = "http://neracoos.org:8080/opendap/" + site + "/" + site + ".aanderaa.realtime.nc"

    try:
        dataset = open_url(url)
    except Exception, e:
        print str(e)
        sys.exit(0)
    print url
    
    lat = dataset['lat']
    lon = dataset['lon']
    time0 = dataset['time']
    u = dataset['current_u']
    v = dataset['current_v']
    depth = dataset['depth']

    current_u = [i for i in u.current_u]
    current_v = [i for i in v.current_v]
    time_num = [(i + time_add_num) for i in time0]        
     
    if len(days) == 1:
        sdate = time_num[0]
        edate = sdate + days[0]
    sdate = time_num[0]
    if len(days) == 2:
        sdate = days[0]
        edate = days[1]

    part_v, part_u, part_time = [], [], []
    for i in range(0, len(current_u)):
        if sdate <= time_num[i] <= edate:
            part_v.append(current_v[i])
            part_u.append(current_u[i])
            part_time.append(time_num[i])
    if float(depth[0]) > 0:
        depth_i = -float(depth[0])
    else:
        depth_i = float(depth[0])

    if len(days) == 1:
        return  part_time, part_u, part_v, float(lat[0]), float(lon[0]), sdate, edate, depth_i
    if len(days) == 2:
        return  part_time, part_u, part_v, float(lat[0]), float(lon[0]), depth_i

def plot_getsst(ask_input, utc, gbox):
    """
    Input:
    ask_input - day you want(format: 2009-08-01 18:34:00)
    utc - 'utc'
    gbox format: [-71, -70.5, 41.25, 41.75]
    """
    
    ask_datetime = dt.datetime.strptime(ask_input, '%Y-%m-%d %H:%M:%S').replace(tzinfo=utc)
    timtzone_ask_datetime = ask_datetime.astimezone(utc)
    second = time.mktime(timtzone_ask_datetime.timetuple())
    year = dt.datetime.strptime(ask_input, '%Y-%m-%d %H:%M:%S').year

    sst, time1, lat, lon = getsst(second)

    # find the index for the gbox
    index_lon1 = int(round(np.interp(gbox[0], list(lon), range(len(list(lon))))))
    index_lon2 = int(round(np.interp(gbox[1], list(lon), range(len(list(lon))))))
    index_lat1 = int(round(np.interp(gbox[2], list(lat), range(len(list(lat))))))
    index_lat2 = int(round(np.interp(gbox[3], list(lat), range(len(list(lat))))))

    # get part of the sst
    sst_part = sst[1839, index_lat1:index_lat2, index_lon1:index_lon2]
    sst_part[(sst_part == -999)] = np.NaN # if sst_part = -999, convert to NaN
    #sst_part[numpy.isnan(sst_part)]=0 # then change NaN to 0
    X, Y = np.meshgrid(lon[index_lon1:index_lon2], lat[index_lat1:index_lat2])
    #plot
    plt.figure()
    # get the min,max of lat and lon
    minlat = min(lat[index_lat1:index_lat2])
    maxlat = max(lat[index_lat1:index_lat2])
    minlon = min(lon[index_lon1:index_lon2])
    maxlon = max(lon[index_lon1:index_lon2])

    # plot map
    basemap_usgs([minlat, maxlat], [minlon, maxlon], False)

    # plot temperature
    CS = plt.contourf(X, Y, sst_part)
    plt.colorbar(CS, format='%1.2g' + 'C')

    # convert the seconds to datetime
    time_tuple = time.gmtime(time1[0])
    plt.title("RU COOL NOAA-19 Sea Surface Temperature: " + 
              dt.datetime(time_tuple.tm_year,
                                time_tuple.tm_mon,
                                time_tuple.tm_mday,
                                time_tuple.tm_hour,
                                time_tuple.tm_min,
                                time_tuple.tm_sec).strftime('%B_%d,%Y %H%M') + " GMT")
    plt.show()


def getsst(second):
    #get the index of second from the url
    time_tuple = time.gmtime(second)#calculate the year from the seconds
    year = time_tuple.tm_year
    if year < 1999 or year > 2010:
        print 'Sorry there might not be available data for this year'
    # WARNING: As of Jan 2012, this data is only stored for 1999-2010
    url1 = 'http://tashtego.marine.rutgers.edu:8080/thredds/dodsC/cool/avhrr/bigbight/' + str(year) + '?time[0:1:3269]'
    dataset1 = open_url(url1)
    times = list(dataset1['time'])
    # find the nearest image index
    index_second = int(round(np.interp(second, times, range(len(times)))))

    #get sst, time, lat, lon from the url
    url = 'http://tashtego.marine.rutgers.edu:8080/thredds/dodsC/cool/avhrr/bigbight/' + \
          str(year) + '?lat[0:1:1221],lon[0:1:1182],' + \
          'mcsst[' + str(index_second) + ':1:' + str(index_second) + \
          '][0:1:1221][0:1:1182]' + \
          ',time[' + str(index_second) + \
          ':1:' + str(index_second) + ']'
    try:
        dataset = open_url(url)
    except:
        print "Please check your url! Cannot access dataset."
        sys.exit(0)

    sst = dataset['mcsst'].mcsst
    time1 = dataset['time']
    lat = dataset['lat']
    lon = dataset['lon']
    return sst, time1, lat, lon

def read_old_mooring_asc(filename):
    """
    Read old mooring data
    Input: filename
    Example data file: "Y:/moor/nech/NEC312b.dat"
    Returns: date_time_number, u, v, y
    """
    try:
        dataReader = csv.reader(open(filename, 'rb'))
    except:
        print "Cannot open file."
        sys.exit(0)
    
    verts = [row for row in dataReader]
    
    del verts[-1], verts[0] #del the first line and last line
    u, v, year, y, hour = [], [], [], [], []
    for i in range(0, len(verts)):
        #convert "space delimiter" to comma
        year.append(verts[i][0].split()[1])
        hour.append(verts[i][0].split()[2])
        u.append(verts[i][0].split()[6])
        v.append(verts[i][0].split()[7])
        y.append(0)
    hour_time = []
    for hour_i in hour:
        hourtime = hour_i[0:2] + ":" + hour_i[2:]
        hour_time.append(hourtime)
    date_time_number = []
    for i in range(0, len(year)):
        datetime = dt.datetime.strptime(year[i] + " " + hour_time[i], '%Y-%m-%d %H:%M')
        date_time_number.append(date2num(datetime))
    u = [float(i) for i in u]
    v = [float(i) for i in v]
    return date_time_number, u, v, y
  
