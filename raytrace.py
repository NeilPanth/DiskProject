#takes 182 seconds under python 3.7, while it took 188 seconds under python 2.7

from scipy import ndimage
from scipy import sign
from astropy.io import fits
import os
#from disk import *
import numpy as np
from astropy import constants as const
from scipy.integrate import cumtrapz,trapz
import math
import matplotlib.pyplot as plt

import sys
np.set_printoptions(threshold=sys.maxsize)
   #Define useful constants
AU = const.au.cgs.value      # - astronomical unit (cm)
c = const.c.cgs.value      # - speed of light (cm/s)
h = const.h.cgs.value     # - Planck's constant (erg/s)
kB = const.k_B.cgs.value    # - Boltzmann's constant (erg/K)
pc = const.pc.cgs.value     # - parsec (cm)
Jy = 1.e23         # - cgs flux density (Janskys)
Msun = const.M_sun.cgs.value    # - solar mass (g)
rad = 206264.806   # - radian to arcsecond conversion
kms = 1e5          # - convert km/s to cm/s
GHz = 1e9          # - convert from GHz to Hz

def gasmodel(disk,params,obs,moldat,tnl, includeDust=False):
    '''Given a disk object, calculate the radiative transfer.
    Return image stack with each slice corresponding to a different velocity channel
    :param disk:
    A Disk object whose structure will be used to calculate the radiative transfer
    :param params:
    A list of parameters, including the mass of the star, inclination, and handedness of the rotation

    :param obs:
    A list of observational parameters including the rest frequency of the observations, the quantum number of the transition, the velocity of the star and the maximum disk height.

    :param moldat:
    Data for this particular molecule

    :param tnl:
    level populations

'''
    l = obs[0]
    nu0 = obs[1]*GHz # - freq0
    Zmax = obs[5]*AU
    veloc = obs[6]*kms


    # - disk parameters
    thet = disk.thet    # - convert inclination into radians
    Mstar = disk.Mstar            # - convert mass of star to grams
    handed = disk.handed               # - handedness of the disk
    wind_speed = params[14]
    wind_angle = params[15]
    min_wind_height = params[16]

    nphi = disk.nphi
    nr = disk.nr
    nz = disk.nz
    S = disk.S

    # - conversions and derivative data
    nu = (veloc)*nu0/c + nu0
    El = moldat['eterm'][l]*h*c
    s0 = h*nu/(4*np.pi)*(2*(l+1.)+1.)/(2.*l+1)*c*c/(2.*h*nu**3)*moldat['A21'][l]

    # - Define some arrays, sizes and useful constants
    kap = 2.3                      # - dust opacity at 1.3mm per H2 mass [cm^2/g]
    BBF1 = 2.*h/(c**2)             # - prefactor for BB function
    BBF2 = h/kB                    # - exponent prefactor for BB function
    SignuF1 = s0*c/(nu0*np.sqrt(np.pi)) # - absorbing cross section prefactor

    # - Calculate source function and absorbing coefficient
    try:
        disk.ecc
    except:
        #Non-eccentric models define disk.Omg
        dV = veloc + (handed*np.sin(thet)*disk.Omg*disk.X[:,:,np.newaxis]*np.ones(nz))


    else:
        #Eccentric models do not have disk.Omg, but use disk.vel instead
        dV = veloc + handed*np.sin(thet)*(disk.vel)


    if wind_speed > 0:
        # add a 'wind'
        #wind_angle = math.radians(wind_angle)
        #calculates wind speed by projecting wind vector onto our line of sight
        #vwind = wind_speed*disk.cs*(disk.heightcutoff*np.cos(thet)*np.cos(wind_angle) + np.sin(thet)*np.sin(wind_angle)*disk.omega)
        #vwind = np.cos(thet)*wind_speed*disk.cs*sign(disk.Z) -- old formula
        dV += disk.vwind
        #adds wind speed to velocities
        #height = disk.calcH(verbose=False)
        #print(height.shape,disk.cs.shape,disk.Z.shape)
    #if wind_speed > 0:
        #vwind = np.cos(thet)*wind_speed*disk.cs*sign(disk.Z)
        #dV += vwind
    elif wind_speed < 0:
        print("Wind speed must be positive, wind not accounted for")

    Signu = SignuF1*np.exp(-dV**2/disk.dBV**2)/disk.dBV*(1.-np.exp(-(BBF2*nu)/disk.T))   # - absorbing cross section


    Knu = tnl*Signu #+ kap*(.01+1.)*disk.rhoG   # - absorbing coefficient
    if includeDust and disk.rhoD is not None:
        Knu_dust = disk.kap*disk.rhoD      # - dust absorbing coefficient
    else:
        Knu_dust = 0*Knu
    Knu+=Knu_dust

    Snu = BBF1*nu**3/(np.exp((BBF2*nu)/disk.T)-1.) # - source function
    if (disk.i_notdisk.sum() > 0):
        Snu[disk.i_notdisk] = 0
        Knu[disk.i_notdisk] = 0
        Knu_dust[disk.i_notdisk] = 0

    #ds = (S-np.roll(S,1,axis=2))/2.
    #arg = ds*(Knu + np.roll(Knu,1,axis=2))
    #arg[:,:,0]=0.
    #tau = arg.cumsum(axis=2)
    tau = cumtrapz(Knu,S,axis=2,initial=0)
    arg = Knu*Snu*np.exp(-tau)

    return trapz(arg,S,axis=2),tau,cumtrapz(arg,S,axis=2,initial=0.)#tau

def calculateTemp(disk):
    '''Given a disk object, calculate the temperature at a certian radius'''

def dustmodel(disk,nu):
    '''Given a disk object, calculate the radiative transfer for the dust.

    :param disk:
    A Disk object whose structure will be used to calculate the radiative transfer

    :param nu:
    Frequency, in GHz, of dust emission

'''
    nu *=GHz

    nphi = disk.nphi
    nr = disk.nr
    nz = disk.nz
    S = disk.S

    # - Define some arrays, sizes and useful constants
    kap = disk.kap                 # - dust opacity at 1.3mm per H2 mass [cm^2/g] (default=2.3)
    BBF1 = 2.*h/(c**2)             # - prefactor for BB function
    BBF2 = h/kB                    # - exponent prefactor for BB function


    Knu_dust = kap*disk.rhoD      # - dust absorbing coefficient
    Snu = BBF1*nu**3/(np.exp((BBF2*nu)/disk.T)-1.) # - source function
    if (disk.i_notdisk.sum() > 0):
        Knu_dust[disk.i_notdisk] = 0


    #ds = (S-np.roll(S,1,axis=2))/2.
    #arg = ds*(Knu_dust + np.roll(Knu_dust,1,axis=2))
    #arg[:,:,0]=0.
    #tau = arg.cumsum(axis=2)
    tau = cumtrapz(Knu_dust,S,axis=2,initial=0.)
    arg = Knu_dust*Snu*np.exp(-tau)
    arg[:,:,0] = 0.


    return trapz(arg,S,axis=2),tau

def total_model(disk,imres=0.05,distance=122.,nchans=15, chanmin = 'autochan', chanstep=0.32,flipme=True,Jnum=2,freq0=345.79599,xnpix=512,vsys=5.79,PA=312.46,offs=[0.0,0.0],modfile='testpy_alma',abund=1.,obsv=None, isgas=True,includeDust=False,extra=0,bin=1,hanning=False):
    '''Run all of the model calculations given a disk object.
    Outputs are a fits file with the model images, along with visibility files (one in miriad format and one in fits format) for this model

    :param disk:
    A Disk object. This contains the structure of the disk over which the radiative transfer calculation will be done.

    :param imres:
    Model image resolution in arcsec. Should be the pixel size in the data image.

    :param distance:
    Distance in parsec to the target

    :param chanmin:
    Minimum channel of the model, by default is automatically set such that the middle channel's value is zero

    :param nchans:
    Number of channels to model

    :param chanstep:
    Resolution of each channel, in km/sec

    :param flipme:
    To save time, the code can calculate the radiative transfer for half of the line, and then mirror these results to fill in the rest of the line. Set flipme=1 to perform this mirroring, or use flipme=0 to compute the entire line profile

    :param Jnum:
    The lower J quantum of the transition of interest. Ex: For the CO J=3-2 transition, set Jnum=2

    :param freq0:
    The rest frequency of the transition, in GHz.

    :param xnpix:
    Number of pixels in model image. xnpix*imres will equal the desired width of the image.

    :param vsys:
    Systemic velocity of the star, in km/sec

    :param PA:
    position angle of the disk (updated to 312.46 from Katherine's value)

    :param offs:
    Disk offset from image center, in arcseconds

    :param modfile:
    The base name for the model files. This code will create modfile+'.fits' (the model image)

    :param datfile:
    The base name for the data files. You need to have datfile+'.vis' (data visibilities in miriad uv format) and datfile+'.cm' (cleaned map of data) for the code to work. The visibility file is needed when running uvmodel and the cleaned map is needed for the header keywords.

    :param miriad:
    Set to True to call a set of miriad tasks that convert the model fits image to a visbility fits file. If this is False, then there is no need to set the datfile keyword (the miriad tasks are the only place where they are used).

    :param abund:
    This code assumes that you are working with the dominant isotope of CO. If this is not the case, then use the abund keyword to set the relative abundance of your molecule (e.g. 13CO or C18O) relative to CO.

    :param obsv:
    Velocities of the channels in the observed line. The model is interpolated onto these velocities, accounting for vsys, the systematic velocity

    :param wind_speed:
    A constant that multiplies the local sound speed to get the wind speed, this changes how much the wind will affect the model. A wind speed of 0 means no wind

    :param wind_angle:
    The angle in degrees that the wind deviates radially outward from the normal line. This changes the dirction the wind goes, with a value of zero being perpendicular to the disk.

    :param isgas:
    Do the modeling of a gas line instead of just continuum. Setting isgas to False will only calculate dust continuum emission at the specified frequency.

    :param includeDust:
    Set to True if you want to include dust continuum in the radiative transfer calculation. This does not calculate a separate continuum image (set isgas=False for that to happen) but instead include dust radiative transfer effects in the gas calculations (e.g. dust is optically thick and obscuring some of the gas photons from the midplane)


    :param extra:
    A parameter to control what extra plots/data are output. The options are 1 (figure showing the disk structure with the tau=1 surface marked with a dashed line), 2.1(a list of the heights as a function of radius between which 50% of the flux arises), 2.2(a list of temperatures as a function of radius between which 50% of the flux arises), 3.0(channel maps showing height of tau=1 surface), 3.1(channel maps showing the temperature at the tau=1 surface), 3.2 (channel maps showing the maximum optical depth)


    :param bin: (default=1)
    If you are comparing to data that has been binned from the native resolution, then you can include that binning in the models. e.g. If the data have been binned down by a factor of two, then set bin=2. This ensures that the model goes through similar processing as the data. Note that bin only accepts integer values.

    :param hanning: (default=False)
    Set to True to perform hanning smoothing on a spectrum. Hanning smoothing is designed to reduce Gibbs ringing, which is associated with the finite time sampling that is used in the generation of a spectrum within an interferometer. Hanning smoothing is included as a running average that replaces the flux in channel i with 25% of the flux in channel i-1, 50% of the flux in channel i, and 25% of the flux in channel i+1.

'''

    params = disk.get_params()
    obs = [Jnum,freq0]
    obs2 = disk.get_obs()
    for x in obs2:
        obs.append(x)
    obs.append(0.)

    #automatically sets chanmin
    if chanmin == 'autochan':
        chanmin = (nchans-1) / -2 * chanstep

    #If accounting for binning then decrease the channel width, and increase the number of channels
    if not isinstance(bin,int):
        print('bin must be an integer. Setting bin=1')
        bin = 1
    nchans *= bin
    chanstep/=bin
    chanmin -= (bin-1)*chanstep/2.

    if nchans==1:
        flipme=False

    xpixscale = imres
    dd = distance*pc    # - distance in cm
    arcsec = rad/dd     # - angular conversion factor (cm to arcsec)
    chans = chanmin+np.arange(nchans)*chanstep
    tchans = chans.astype('|S6') # - convert channel names to string

    # extract disk structure from Disk object
    cube=np.zeros((disk.nphi,disk.nr,nchans))
    cube2=np.zeros((disk.nphi,disk.nr,disk.nz,nchans)) #tau
    cube3 = np.zeros((disk.nphi,disk.nr,disk.nz,nchans)) #tau_dust
    X = disk.X
    Y = disk.Y

    if isgas:
    # approximation for partition function
        try:
            #The code recognizes 13CO(2-1), C18O(2-1), DCO+(3-2), HCO+(4-3), HCN(4-3), CO(3-2), CS(7-6), CO(1-0), CO(2-1), CO(6-5), DCO+(5-4), DCO+(4-3), C18O(3-2), C18O(1-0)
            if Jnum == 1 and np.abs(freq0-220.398677) < .1:
                moldat = mol_dat(file='13co.dat')
            elif Jnum==1 and np.abs(freq0-219.56036) < .1:
                moldat = mol_dat(file='c18o.dat')
            elif Jnum==2 and np.abs(freq0-216.11258)<1:
                moldat = mol_dat(file='dcoplus.dat')
            elif Jnum ==3 and np.abs(freq0-356.734223)<0.1:
                moldat = mol_dat(file='hcoplus.dat')
            elif Jnum==3 and np.abs(freq0-354.50547590)<0.1:
                moldat = mol_dat(file='hcn.dat')
            elif Jnum==2 and np.abs(freq0-345.7959899)<0.1:
                moldat = mol_dat(file='co.dat')
            elif Jnum==6 and np.abs(freq0-342.88285030)<0.1:
                moldat = mol_dat(file='cs.dat')
            elif Jnum==0 and np.abs(freq0-115.2712)<0.1:
                moldat = mol_dat(file='co.dat')
            elif Jnum==1 and np.abs(freq0-230.538)<0.1:
                moldat = mol_dat(file='co.dat')
            elif Jnum==5 and np.abs(freq0-691.4730763)<0.1:
                moldat = mol_dat(file='co.dat')
            elif Jnum==2 and np.abs(freq0-329.3305525)<0.1:
                moldat = mol_dat(file='c18o.dat')
            elif Jnum == 0 and np.abs(freq0-109.7821734)<0.1:
                moldat = mol_dat(file='c18o.dat')
            elif Jnum==4 and np.abs(freq0-360.16978)<0.1:
                moldat = mol_dat(file='dcoplus.dat')
            elif Jnum==3 and np.abs(freq0-288.143858)<0.1:
                moldat = mol_dat(file='dcoplus.dat')
            else:
                raise ValueError('Make sure that Jnum and freq0 match one of: 13CO(2-1), C18O(2-1), DCO+(3-2), HCO+(4-3), HCN(4-3), CO(3-2), CS(7-6), CO(1-0), CO(2-1), CO(6-5), DCO+(5-4), DCO+(4-3), C18O(3-2), C18O(1-0)')
        except:
            raise
        gl = 2.*obs[0]+1
        El = moldat['eterm'][obs[0]]*h*c # - energy of lower level
        Te = 2*El/(obs[0]*(obs[0]+1)*kB)
        parZ = np.sqrt(1.+(2./Te)**2*disk.T**2)

    # calculate level population
        tnl = gl*abund*disk.rhoG*np.exp(-(El/kB)/disk.T)/parZ
        w = tnl<0
        if w.sum()>0:
            tnl[w] = 0


    # Do the calculation
    if flipme & (nchans % 2==0):
        dchans = int(nchans/2.)
    elif flipme & (nchans % 2 ==1):
        dchans = int(nchans/2.+0.5)
    else:
        dchans = nchans


    for i in range(int(dchans)):
        obs[6] = chans[i]  # - vsys
        if isgas:
            Inu,Inuz,tau_dust = gasmodel(disk,params,obs,moldat,tnl,includeDust=includeDust)
        #Inu_dust,tau_dust = dustmodel(disk,freq0)
            cube[:,:,i] = Inu
        #print('Finished channel %i / %i' % (i+1,nchans))
            cube2[:,:,:,i] = Inuz
            cube3[:,:,:,i] = tau_dust
        else:
            Inu,tau_dust = dustmodel(disk,freq0)
            cube[:,:,i] = Inu
            cube2[:,:,:,i] = tau_dust
    if flipme:
        cube[:,:,dchans:] = cube[:,:,-(dchans+1):-(nchans+1):-1]
        cube2[:,:,:,dchans:] = cube2[:,:,:,-(dchans+1):-(nchans+1):-1]
        cube3[:,:,:,dchans:] = cube3[:,:,:,-(dchans+1):-(nchans+1):-1]

    if extra == 1 :
        # plot tau=1 surface in central channel
        plot_tau1(disk,cube2[:,:,:,int(nchans/2-1)],cube3[:,:,:,int(nchans/2-1)])
    if (extra == 2.1) or (extra==2.2):
        for r in range(10,500,20):#20
            if extra > 2.1:
                flux_range(disk,cube3,r,height=False) #cube3 is cumulative flux along each sight line [nr,nphi,ns,nchan]
            else:
                flux_range(disk,cube3,r,height=True)
    if extra>2.5:
        print('*** Creating tau=1 image ***')
        ztau1tot=np.zeros((disk.nphi,disk.nr,nchans))
        for i in range(int(nchans)):
            ztau1tot[:,:,i] = findtau1(disk,cube2[:,:,:,i],cube[:,:,i],cube3[:,:,:,i],flag=extra-3)
            #ztau1tot[:,:,i] = cube2[:,:,290,i]*Disk.AU
        #now create images of ztau1, similar to images of intensity
        imt = xy_interpol(ztau1tot,X*arcsec,Y*arcsec,xnpix=xnpix,imres=imres,flipme=flipme)
        imt[np.isnan(imt)]=-170*disk.AU
        velo = chans+vsys
        tvelo = velo.astype('|S6') # - convert channel names to string
        print(tvelo)
        if obsv is not None:
            imt2 = np.zeros((xnpix,xnpix,len(obsv)))
            for ix in range(xnpix):
                for iy in range(xnpix):
                    if velo[1]-velo[0]<0:
                        imt2[ix,iy,:]=np.interp(obsv,velo[::-1],imt[ix,iy,::-1])
                        #imt[ix,iy,:]=imt[ix,iy,::-1]
                    else:
                        imt2[ix,iy,:]=np.interp(obsv,velo,imt[ix,iy,:])
            hdrt=write_h(nchans=len(obsv),dd=distance,xnpix=xnpix,xpixscale=xpixscale,lstep=chanstep,vsys=vsys)
        else:
            imt2=imt
            hdrt=write_h(nchans=nchans,dd=distance,xnpix=xnpix,xpixscale=xpixscale,lstep=chanstep,vsys=vsys)
        #imt2[np.isnan(imt2)] = -170*disk.AU
        #imt2[np.isinf(imt2)] = -170*disk.AU
        imt_s=ndimage.rotate(imt2,90.+PA,reshape=False)
        pixshift=np.array([-1.,1.])*offs/(3600.*np.abs([hdrt['cdelt1'],hdrt['cdelt2']]))
        imt_s = ndimage.shift(imt_s,(pixshift[0],pixshift[1],0),mode='nearest')
        hdut=fits.PrimaryHDU((imt_s/disk.AU).T,hdrt)
        #hdut=fits.PrimaryHDU((imt_s).T,hdrt)
        hdut.writeto(modfile+'p_tau1.fits',overwrite=True,output_verify='fix')


    # - interpolate onto a square grid
    im = xy_interpol(cube,X*arcsec,Y*arcsec,xnpix=xnpix,imres=imres,flipme=flipme)

    if isgas:
    # - interpolate onto velocity grid of observed star
        velo = chans+vsys
        if obsv is not None:
            obsv2 = np.arange(len(obsv)*bin)*(obsv[1]-obsv[0])/bin+obsv[0]
            im2 = np.zeros((xnpix,xnpix,len(obsv2)))
            for ix in range(xnpix):
                for iy in range(xnpix):
                    if velo[1]-velo[0] < 0:
                        im2[ix,iy,:] = np.interp(obsv2,velo[::-1],im[ix,iy,::-1])
                    else:
                        im2[ix,iy,:] = np.interp(obsv2,velo,im[ix,iy,:])
        else:
            im2=im

    if hanning:
        im2 = perform_hanning(im2)

    if bin > 1:
        new_im = np.zeros((im2.shape[0],im2.shape[1],im2.shape[2]//bin))
        for k in range(new_im.shape[2]):
            new_im[:,:,k] = np.mean(im2[:,:,k*bin:k*bin+bin],axis=2)
        im2 = new_im
        nchans/=bin
        chanstep*=bin
        chans = chanmin+np.arange(nchans)*chanstep


    # - make header
    if isgas:
        if obsv is not None:
            hdr =  write_h(nchans=len(obsv),dd=distance,xnpix=xnpix,xpixscale=xpixscale,lstep=chanstep,vsys=vsys)
        else:
            hdr =  write_h(nchans=nchans,dd=distance,xnpix=xnpix,xpixscale=xpixscale,lstep=chanstep,vsys=vsys)
    else:
        im2=im
        hdr = write_h_cont(dd=distance,xnpix=xnpix,xpixscale=xpixscale)
    # - shift and rotate model
    im_s = ndimage.rotate(im2,90.+PA,reshape=False) #***#

    pixshift = np.array([-1.,1.])*offs/(3600.*np.abs([hdr['cdelt1'],hdr['cdelt2']]))
    im_s = ndimage.shift(im_s,(pixshift[0],pixshift[1],0),mode='nearest')*Jy*(xpixscale/rad)**2


    # write processed model
    hdu = fits.PrimaryHDU(im_s.T,hdr)
    hdu.writeto(modfile+'.fits',overwrite=True,output_verify='fix')

def perform_hanning(cube):
    '''Apply hanning smoothing over an image.'''

    if len(cube.shape)==3:
        test_cube = np.zeros(cube.shape)
        for k in range(1,cube.shape[2]-1):
            test_cube[:,:,k] = .25*cube[:,:,k-1]+.5*cube[:,:,k]+.25*cube[:,:,k+1]
        test_cube[:,:,0] = .625*cube[:,:,0]+.275*cube[:,:,1]
        test_cube[:,:,-1] = .625*cube[:,:,-1]+.275*cube[:,:,-2]
    if len(cube.shape)==4:
        test_cube = np.zeros(cube.shape)
        for k in range(1,cube.shape[3]-1):
            test_cube[:,:,:,k] = .25*cube[:,:,:,k-1]+.5*cube[:,:,:,k]+.25*cube[:,:,:,k+1]
        test_cube[:,:,:,0] = .625*cube[:,:,:,0]+.275*cube[:,:,:,1]
        test_cube[:,:,:,-1] = .625*cube[:,:,:,-1]+.275*cube[:,:,:,-2]

    return test_cube


def write_h(nchans,dd,xnpix,xpixscale,lstep,vsys):
    'Create a header for the output image'
    hdr = fits.Header()
    cen = [xnpix/2.+.5,xnpix/2.+.5]   # - central pixel location

    hdr['SIMPLE']='T'
    hdr['BITPIX'] = 32
    hdr['NAXIS'] = 3
    hdr['NAXIS1'] = xnpix
    hdr['NAXIS2'] = xnpix
    hdr['NAXIS3'] = nchans
    hdr['CDELT1'] = -1.*xpixscale/3600.
    hdr['CRPIX1'] = cen[0]
    hdr['CRVAL1'] = 0.
    hdr['CTYPE1'] = 'RA---SIN'
    hdr['CDELT2'] = xpixscale/3600.
    hdr['CRPIX2'] = cen[1]
    hdr['CRVAL2'] = 0.
    hdr['CTYPE2'] = 'DEC--SIN'
    hdr['CTYPE3'] = 'VELO-LSR'
    hdr['CDELT3'] = lstep*1000    # - dv im m/s
    hdr['CRPIX3'] = nchans/2+1.    # - 0 velocity channel
    hdr['CRVAL3'] = vsys*1e3      # - has zero velocity
    hdr['OBJECT'] = 'model'
    hdr['EPOCH'] = 2000.
    #hdr['RESTFREQ']=219.5604

    return hdr


def write_h_cont(dd,xnpix,xpixscale):
    'Create a header for the output image'
    hdr = fits.Header()
    cen = [xnpix/2.+.5,xnpix/2.+.5]   # - central pixel location

    hdr['SIMPLE']='T'
    hdr['BITPIX'] = 32
    hdr['NAXIS'] = 3
    hdr['NAXIS1'] = xnpix
    hdr['NAXIS2'] = xnpix
    hdr['CDELT1'] = -1.*xpixscale/3600.
    hdr['CRPIX1'] = cen[0]
    hdr['CRVAL1'] = 0
    hdr['CTYPE1'] = 'RA---SIN'
    hdr['CDELT2'] = xpixscale/3600.
    hdr['CRPIX2'] = cen[1]
    hdr['CRVAL2'] = 0
    hdr['CTYPE2'] = 'DEC--SIN'
    hdr['OBJECT'] = 'model'

    return hdr

def xy_interpol(cube,dec,ra,xnpix,imres,flipme=0):
    'Interpolate the model onto a square grid'

    # - initialize grids
    nchans = cube.shape[2]
    npix = [xnpix,xnpix]
    nx = npix[0]
    ny = npix[1]
    pPhi = np.zeros((nx,ny))

    sqcube = np.zeros((xnpix,xnpix,nchans))
    thing = dec.shape
    nphi = thing[0]
    nr = thing[1]
    sY = ( ((np.arange(npix[1])+0.5)*imres-imres*npix[1]/2.)[:,np.newaxis]*np.ones(nx)).transpose()
    sX = ((np.arange(npix[0])+0.5)*imres-imres*npix[0]/2.).repeat(ny).reshape(nx,ny)
    dx = sX[1,0] - sX[0,0]
    dy = sY[0,1] - sY[0,0]

    pR = np.sqrt(sX**2+sY**2)
    pPhi = np.arccos(sX/pR)
    pPhi[(sY <=0)] = 2*np.pi - pPhi[(sY <= 0)]
    pPhi = pPhi.flatten()
    pR = pR.flatten()

    r = (np.sqrt(dec*dec+ra*ra))[0,:]
    phi = np.arange(nphi)*2*np.pi/(nphi-1)

    # - do interpolation
    iR = np.interp(pR,r,range(nr))
    iPhi = np.interp(pPhi,phi,range(nphi))

    if flipme:
        dchans = nchans/2. + 0.5
    else:
        dchans = nchans

    w = (pR>r.max()).reshape(xnpix,xnpix)
    for i in range(int(dchans)):
        sqcube[:,:,i] = ndimage.map_coordinates(cube[:,:,i],[[iPhi],[iR]],order=1).reshape(xnpix,xnpix)
        sqcube[:,:,i][w] = 0.


    if flipme:
        sX = -1*((np.arange(npix[0])+0.5)*imres-imres*npix[0]/2.).repeat(ny).reshape(nx,ny)
        dx = sX[1,0] - sX[0,0]

        pR = np.sqrt(sX**2+sY**2)
        pPhi = np.arccos(sX/pR)
        pPhi[(sY <=0)] = 2*np.pi - pPhi[(sY <= 0)]
        pPhi = pPhi.flatten()
        pR = pR.flatten()

        r = (np.sqrt(dec*dec+ra*ra))[0,:]
        phi = np.arange(nphi)*2*np.pi/(nphi-1)

        # - do interpolation
        iR = np.interp(pR,r,range(nr))
        iPhi = np.interp(pPhi,phi,range(nphi))

        w = (pR>r.max()).reshape(xnpix,xnpix)
        for i in range(int(dchans),nchans):
            sqcube[:,:,i] = ndimage.map_coordinates(cube[:,:,i],[[iPhi],[iR]],order=1).reshape(xnpix,xnpix)
            sqcube[:,:,i][w] = 0.

    return sqcube

def findtau1(disk,tau,Inu,cube3,flag=0.):
    r = disk.r
    nr = disk.nr
    nphi = disk.nphi
    phi = np.arange(nphi)*2*np.pi/(nphi-1)
    z=disk.Z

    ztau1=np.zeros((nphi,nr))
    for ir in range(nr):
        for iphi in range(nphi):
            #if Inu[iphi,ir]*5e9<4.1e-5:
            #    ztau1[iphi,ir] = -170*disk.AU
            #else:
            if np.float(flag)==0:
                ztau1[iphi,ir]=np.interp(1,tau[iphi,ir,:],z[iphi,ir,:])#tau
            if (flag>0.) & (flag<0.2):
                ztau1[iphi,ir]=np.interp(1,tau[iphi,ir,:],disk.T[iphi,ir,:],right=0.,left=0.)*disk.AU#temp at tau=1 surface (multiplying by AU is because code after this assumes that it is actually height of tau=1 surface)
            #ztau1[iphi,ir] = np.interp(10,tau[iphi,ir,:],cube3[iphi,ir,:])*disk.AU
            #ztau1[iphi,ir] = np.sum(disk.T[iphi,ir,:]*tau[iphi,ir,:])/np.sum(tau[iphi,ir,:])*disk.AU
            if flag>0.1:
                ztau1[iphi,ir] = tau[iphi,ir,:].max()*disk.AU #max optical depth (multiplying by AU is because code after this assumes it is height of tau=1 surface in units of cm)
            #ztau1[iphi,ir]=np.interp(.5*tau[iphi,ir,-1],tau[iphi,ir,:],z[iphi,ir,:])#95% of total flux
            #if tau[iphi,ir,-1]==0:
            #    ztau1[iphi,ir] = -170*disk.AU
            #if (iphi % 50 ==0) & (ir %50==0):
            #    print(tau[iphi,ir,-1],ztau1[iphi,ir]/disk.AU)
    return ztau1
#c18o 2-1: 4.1e-5
#13co 2-1: 5.1e-5
#co 2-1: 1.3e-4
#co 3-2: 3.3e-4


def plot_tau1(disk,tau,tau_dust):
    '''Plot the tau=1 surface on top of the disk structure plot'''
    #ztau1 = findtau1(disk,tau,Inu)
    plt.figure()
    plt.rc('axes',lw=2)
    iphi=21#8#26 (near side of disk)#74 (far side of disk) #21,59 for DCO+
    cs2 = plt.contour(disk.r[iphi,:,:]/disk.AU,disk.Z[iphi,:,:]/disk.AU,np.log10((disk.rhoG/disk.Xmol)[iphi,:,:]),np.arange(0,11,0.1))
    #cs2 = plt.contour(disk.r[iphi,:,:]/disk.AU,disk.Z[iphi,:,:]/disk.AU,np.log10((disk.rhoG)[iphi,:,:]),np.arange(-8,3,0.1))
    #cs2 = plt.contour(disk.r[iphi,:,:]/disk.AU,disk.Z[iphi,:,:]/disk.AU,np.log10((disk.rhoH2)[iphi,:,:]),np.arange(0,11,0.1))
    cs3 = plt.contour(disk.r[iphi,:,:]/disk.AU,disk.Z[iphi,:,:]/disk.AU,np.log10(disk.sig_col[0,:,:]),(-2,-1),linestyles=':',linewidths=3,colors='k')
    #manual_locations=[(300,30),(250,60),(180,50),(180,70),(110,60),(45,30)]
    cs3 = plt.contour(disk.r[iphi,:,:]/disk.AU,disk.Z[iphi,:,:]/disk.AU,disk.T[iphi,:,:],(10,20,30,40,50,60,70,80,90,100,110,120,130,140,150,200,300,400),colors='k',linestyles='--')
    cs = plt.contour(disk.r[iphi,:,:]/disk.AU,disk.Z[iphi,:,:]/disk.AU,tau[iphi,:,:],(1,),colors='k',linestyles='--',linewidths=3)
    cs_dust = plt.contour(disk.r[iphi,:,:]/disk.AU,disk.Z[iphi,:,:]/disk.AU,tau_dust[iphi,:,:],(1,),colors='k',linewidths=3)
    plt.clabel(cs3,fmt='%1i')
    plt.plot(disk.rf/disk.AU,disk.calcH()/disk.AU,color='k')
    #plt.clabel(cs3,fmt='%1i',manual=manual_locations)

    iphi=59#74#32
    cs2 = plt.contour(-disk.r[iphi,:,:]/disk.AU,disk.Z[iphi,:,:]/disk.AU,np.log10((disk.rhoG/disk.Xmol)[iphi,:,:]),np.arange(0,11,0.1)) #H2 number dens in region with mol
    #cs2 = plt.contour(-disk.r[iphi,:,:]/disk.AU,disk.Z[iphi,:,:]/disk.AU,np.log10((disk.rhoG)[iphi,:,:]),np.arange(-8,3,0.1)) #mol number density
    #cs2 = plt.contour(-disk.r[iphi,:,:]/disk.AU,disk.Z[iphi,:,:]/disk.AU,np.log10((disk.rhoH2)[iphi,:,:]),np.arange(0,11,0.1)) #H2 number density throughout disk
    cs3 = plt.contour(-disk.r[iphi,:,:]/disk.AU,disk.Z[iphi,:,:]/disk.AU,np.log10(disk.sig_col[0,:,:]),(-2,-1),linestyles=':',linewidths=3,colors='k')
    manual_locations=[(-300,30),(-250,60),(-180,50),(-180,70),(-110,60),(-45,30)]
    cs3 = plt.contour(-disk.r[iphi,:,:]/disk.AU,disk.Z[iphi,:,:]/disk.AU,disk.T[iphi,:,:],(10,20,30,40,50,60,70,80,90,100,110,120,130,140,150,200,300,400),colors='k',linestyles='--')
    cs = plt.contour(-disk.r[iphi,:,:]/disk.AU,disk.Z[iphi,:,:]/disk.AU,tau[iphi,:,:],(1,),colors='k',linestyles='--',linewidths=3)
    cs_dust = plt.contour(-disk.r[iphi,:,:]/disk.AU,disk.Z[iphi,:,:]/disk.AU,tau_dust[iphi,:,:],(1,),colors='k',linewidths=3)
    plt.plot(-disk.rf/disk.AU,disk.calcH()/disk.AU,color='k')
    #print('H: ',disk.rf/disk.AU,disk.calcH()/disk.AU)

    ax = plt.gca()
    for tick in ax.xaxis.get_major_ticks():
        tick.label1.set_fontsize(14)
        tick.label1.set_fontweight('bold')
    for tick in ax.yaxis.get_major_ticks():
        tick.label1.set_fontsize(14)
        tick.label1.set_fontweight('bold')
    plt.clabel(cs3,fmt='%1i')
    #plt.clabel(cs3,fmt='%1i',manual=manual_locations)
    plt.colorbar(cs2,label='log n')
    plt.xlim(-700,700)
    plt.xlabel('R (AU)',fontsize=20)
    plt.ylabel('Z (AU)',fontsize=20)
    plt.ylim(-150,150)
    plt.show()
    #iphi=74#26 (near side of disk)#74 (far side of disk)
    #cs = plt.contour(disk.r[iphi,:,:]/disk.AU,disk.Z[iphi,:,:]/disk.AU,tau[iphi,:,:],(1,),colors='k',linestyles='--',linewidths=3)

    #for i in range(disk.get_obs()[1]):
    #    print(i,tau[i,:,:].max())

def flux_range(disk,cube3,r0,height=True):
    ''' For a given radius, derive the range of heights over which 25%-75% of the flux originate.'''
    r0*= disk.AU
    radius = disk.r
    z = disk.Z/disk.AU
    nchans = cube3.shape[3]
    ztau_all = np.array([])
    flux_all = np.array([])
    w = (radius>(r0-10*disk.AU)) & (radius<(r0+10*disk.AU))
    for iv in range(nchans):
        cube3v = cube3[:,:,:,iv]-np.roll(cube3[:,:,:,iv],1,axis=2)
        if height:
            ztau_all = np.concatenate((ztau_all,cube3v[w]*z[w]))
        else:
            ztau_all = np.concatenate((ztau_all,cube3v[w]*disk.T[w]))
        flux_all = np.concatenate((flux_all,cube3v[w]))

    w = flux_all>0
    ztau_all = ztau_all[w]/flux_all[w]
    flux_all = flux_all[w]

    wuse = flux_all>.05*flux_all.max()
    w = np.argsort(ztau_all[wuse])
    if height:
        print('R, Z(25%), Z(75%): ',r0/disk.AU,ztau_all[wuse][w][int(.25*len(w))],ztau_all[wuse][w][int(.75*len(w))])
    else:
        print('R, T(25%), T(75%): ',r0/disk.AU,ztau_all[wuse][w][int(.25*len(w))],ztau_all[wuse][w][int(.75*len(w))])


def mol_dat(file='co.dat'):
    import numpy as np
    codat = open(file,'r')
    sdum = codat.readline()
    specref = (codat.readline())[:-1]
    sdum = codat.readline()
    amass = float(codat.readline())
    sdum = codat.readline()
    nlev = int(codat.readline())
    sdum = codat.readline()

    #Read in energy levels
    eterm = np.zeros(nlev)
    gstat = np.zeros(nlev)
    for i in range(nlev):
        idum, ieterm, igstat, idum = (codat.readline()).split()
        eterm[i]=(float(ieterm))
        gstat[i]=(float(igstat))


    # Read in radiative transitions
    sdum = codat.readline()
    nrad = int(codat.readline())
    sdum = codat.readline()

    A21 = np.zeros(nrad)
    freq = np.zeros(nrad)
    Eum = np.zeros(nrad)
    for i in range(nrad):
        idum,idum2,idum3,iA21,ifreq,iEum = (codat.readline()).split()
        A21[i] = float(iA21)
        freq[i] = float(ifreq)
        Eum[i] = float(iEum)


    codat.close()

    return {'eterm':eterm,'gstat':gstat,'specref':specref,'amass':amass,'nlev':nlev,'A21':A21,'Eum':Eum}
