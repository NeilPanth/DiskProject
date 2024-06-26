from disk import *
import numpy as np
import matplotlib.pyplot as plt
from raytrace import *
from mpl_toolkits import mplot3d
import sys
from astropy.io import fits
from mcmc_helper3 import *

#Example disk generation
#turn flipme off for wind models since wind causes asymmetry!

x = Disk()
x.set_incl(30)
x.set_wind_speed(0.1)
x.set_wind_angle(30)
x.set_min_wind_height(0.15)
x.set_structure()
x.set_rt_grid()
x.get_params()
total_model(x, nchans = 30, chanstep = 0.08, flipme = False, modfile = 'TEST2_0.1wind_30angle_0.15height')


#Finds difference between left and right peak of disk's spectra
'''def find_peak_difference(filename):
    image = fits.open(filename)
    image_data = image[0].data
    nchans = np.shape(image_data)[0]
    veloc, spec = im_plot_spec(filename)
    spec1 = spec[0:int(nchans/2)]
    spec2 = spec[int(nchans/2):int(nchans)]
    print(np.max(spec1)/np.max(spec2))

peaks30 = np.array([0.851, 0.851, 0.861, 0.887, 0.938])
peaks45 = np.array([0.887, 0.893, 0.909, 0.943, 0.970])
peaks60 = np.array([0.935, 0.942, 0.957, 0.973, 0.991])

base = np.array([0, 15, 30, 45, 60])

plt.plot(base, peaks30)
plt.plot(base, peaks45)
plt.plot(base, peaks60)
plt.legend(["30\N{DEGREE SIGN} inclination", "45\N{DEGREE SIGN} inclination", "60\N{DEGREE SIGN} inclination"])
plt.xlabel("Wind Angle (\N{DEGREE SIGN})")
plt.ylabel("Ratio of peak fluxes")
plt.show()'''