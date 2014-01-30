"""
Detection of (self-) eclipsed faces in a mesh.

These algorithms handle different cases for detecting eclipses and the horizon.
Some are general, others only handle convex hulls etc.

.. autosummary::

    detect_eclipse_horizon
    detect_eclipse_horizon_fast
    horizon_via_normal
    convex_qhull
"""
import logging
import numpy as np
import pylab as pl
import scipy as sp

try:
    from scipy.spatial import cKDTree as KDTree
    KDTree.query_ball_point    
except AttributeError:
    from scipy.spatial import KDTree

from phoebe.algorithms import fraytracing
from phoebe.algorithms import fconvex
from phoebe.algorithms import ceclipse


logger = logging.getLogger('ALGO.ECLIPSE')

def detect_eclipse_horizon(body_list,threshold=1.25*np.pi,tolerance=1e-6):
    """
    Detect (self) (partially) eclipsed triangles in a mesh.
    
    There is a distinction between triangles wich are completely eclipsed
    (C{hidden}) and partially eclipsed (C{hidden_partial}).
    
    Triangles at the horizon are typically also partially eclipsed.
    
    Z-component of centers are used to sort the triangles from front to back.
    This is an internal operation which is undone at the end of this function,
    before returning results. The user should only be B{aware} that the Z
    direction is the line-of-sight (from -inf to +inf; object at -10 is closer
    to the observer than an object at -5 or +4). But this should change in
    the near future (or is already changed).
    
    Threshold is some parameter that I don't exactly remember why it's there.
    I think it skips checking triangles facing backwards.
    
    """
    if not isinstance(body_list,list): body_list = [body_list]
    mesh_list = [body.mesh for body in body_list]
    #-- identify components before merging
    Ns = [len(mesh) for mesh in mesh_list]
    Ns = [0] + list(np.cumsum(Ns))
    
    #-- merge mesh
    mesh = np.hstack(mesh_list)
    #-- sort from front to back, and remember the inverse sorting to return the
    #   results in the order received back to the user
    sa = np.argsort(mesh['center'][:,2])[::-1] # inverted!
    sa_inv = np.argsort(sa)
    mesh = mesh[sa]
        
    #-- prepare arrays to collect information on hidden/partially hidden
    #   triangles
    N = len(mesh)
    hidden = np.zeros(N,int)
    hidden_partial = np.zeros(N,int)
    hidden_vertices = np.zeros((N,3),int)
    hiding_partial = np.zeros(N,int)
    #-- do detection
    hidden,hidden_partial,hidden_vertices,hiding_partial = \
         fraytracing.fine(mesh['triangle'],mesh['normal_'],threshold,tolerance,\
                         hidden,hidden_partial,\
                         hidden_vertices,hiding_partial)
    #-- construct boolean arrays
    hidden = hidden>-1
    hidden_partial = (hidden_partial>-1)
    #-- make a distinction between visible and partialy visible triangles
    visible = -hidden        & -hidden_partial
    partial = hidden_partial & -hidden
    #-- add to the total mesh
    if not 'hidden' in mesh.dtype.names:
        mesh = pl.rec_append_fields(mesh,['hidden','visible','partial'],[hidden,visible,partial])
    else:
        mesh['hidden'] = hidden
        mesh['visible']= visible
        mesh['partial']= partial
    N = float(N)/100.
    #logger.info("detected eclipse and horizon ({0:d} faces): {1:.1f}%/{2:d} hidden, {3:.1f}%/{4:d} visible, {5:.1f}%/{6:d} partial visible".format(int(N*100),sum(hidden)/N,sum(hidden),sum(visible)/N,sum(visible),sum(partial)/N,sum(partial)))
    
    mesh = mesh[sa_inv]
    #-- divided it in the number of components again
    mesh_list_out = [mesh[N1:N2] for N1,N2 in zip(Ns,Ns[1:])]
    #-- and make sure to copy the original attributes
    for i in range(len(body_list)):
        #if isinstance(body_list[i],Body):
        body_list[i].mesh = mesh_list_out[i]
    if len(body_list)==1:
        body_list = body_list[0]    
    #-- that's it!
    

def detect_eclipse_horizon_fast(body_list,tolerance=1e-6):
    """
    Same as above (hopefully) except faster.
    """
    
    if not isinstance(body_list,list): 
        body_list = [body_list]
    
    mesh_list = [body.mesh for body in body_list]
    
    Ns = [len(mesh) for mesh in mesh_list]
    Ns = [0] + list(np.cumsum(Ns))
    
    mesh = np.hstack(mesh_list)
    
    tab = mesh['triangle']
    N = len(tab)
    
    st = np.argsort(mesh['center'][:,2])[::-1]
    STp = np.vstack((tab[st][:,0:3],tab[st][:,3:6],tab[st][:,6:9]))
    STp = np.hstack((STp,np.tile(range(N),3).reshape(3*N,1),np.repeat((0,1,2),N).reshape(3*N,1)))
    stpi = np.lexsort((STp[:,3],STp[:,0],STp[:,1],STp[:,2]))
    sp = STp[stpi]
    
    v,p,h = ceclipse.decl(tab,st,sp,tolerance)
    
    visible = np.zeros(N,bool)
    visible[v] = True
    partial = np.zeros(N,bool)
    partial[p] = True
    hidden= np.zeros(N,bool)
    hidden[h] = True
    
    if not 'hidden' in mesh.dtype.names:
        mesh = pl.rec_append_fields(mesh,['hidden','visible','partial'],[hidden,visible,partial])
    else:
        mesh['hidden'] = hidden
        mesh['visible']= visible
        mesh['partial']= partial

    mesh_list_out = [mesh[N1:N2] for N1,N2 in zip(Ns,Ns[1:])]    
    for i in range(len(body_list)):
        body_list[i].mesh = mesh_list_out[i]
    if len(body_list)==1:
        body_list = body_list[0]
    
    
def horizon_via_normal_old(body_list):
    """
    Detect horizon via the sign of the mu angle (no eclipses).
    
    This function is the simplest type of horizon detection and only works
    for unobscuring convex bodies. It sets all the triangles that have a
    normal point towards the observer (mu>0) to be visible, and the rest
    invisible. There is no partial visibility defined, although it could
    be extended to include those that have mu angle of zero (with some
    tolerance limit).
    
    @param body_list: list of bodies
    @type body_list: list
    """
    if not isinstance(body_list,list):
        body_list = [body_list]
    mesh_list = [body.mesh for body in body_list]
    #-- identify components before merging
    Ns = [len(mesh) for mesh in mesh_list]
    Ns = [0] + list(np.cumsum(Ns))
        
    #-- merge mesh
    mesh = np.hstack(mesh_list)
    visible = mesh['mu']>0
    hidden = -visible
    partial = np.zeros(len(mesh),bool)
    #-- add to the total mesh
    if not 'hidden' in mesh.dtype.names:
        mesh = pl.rec_append_fields(mesh,['hidden','visible','partial'],[hidden,visible,partial])
    else:
        mesh['hidden'] = hidden
        mesh['visible']= visible
        mesh['partial']= partial
    
    #-- divided it in the number of components again
    mesh_list_out = [mesh[N1:N2] for N1,N2 in zip(Ns,Ns[1:])]
    #-- and make sure to copy the original attributes
    for i in range(len(body_list)):
        #if isinstance(body_list[i],Body):
        body_list[i].mesh = mesh_list_out[i]
    if len(body_list)==1:
        body_list = body_list[0]    
    #-- that's it!

def horizon_via_normal(body_list):
    """
    Detect horizon via the sign of the mu angle (no eclipses).
    
    This function is the simplest type of horizon detection and only works
    for unobscuring convex bodies. It sets all the triangles that have a
    normal point towards the observer (mu>0) to be visible, and the rest
    invisible. There is no partial visibility defined, although it could
    be extended to include those that have mu angle of zero (with some
    tolerance limit).
    
    @param body_list: list of bodies
    @type body_list: list
    """
    # Possible a BodyBag is given, in that case take the separate Bodies
    #if hasattr(body_list, 'bodies'):
    #    body_list = body_list.bodies
    
    # Possible a Body is given, make sure to make it into a list
    if hasattr(body_list, 'params'):
        body_list = [body_list]
    
    # Cycle over all Bodies
    for body in body_list:
        # If the Body is a BodyBag, recursively compute its horizon. If we'd
        # want to do this for the whole body immediately, we risk having to
        # copy the mesh (because merged meshes of BodyBags are not directly
        # accessible)
        if hasattr(body, 'bodies'):
            horizon_via_normal(body.bodies)
            continue
        
        # Else we have a normal Body
        mesh = body.mesh
        visible = mesh['mu'] > 0
        mesh['hidden'] = -visible
        mesh['visible']=  visible
        mesh['partial']= 0.0
    return False
    
    
def convex_qhull(body_list):
    """
    Eclipse detection via QHull and Delaunay triangulation.
    
    @param body_list: list of bodies
    @type body_list: list of Bodies
    """
    if not isinstance(body_list,list):
        body_list = [body_list]
    
    # Make sure some defaults are set
    horizon_via_normal(body_list)
    
    # Order the bodies from front to back. Now I do a very crude approximation
    # that can break down once you have small body very near the surface
    # of the other body. I simply order them according to the location of
    # the first triangle in the mesh.
    location = np.argsort([bb.mesh['center'][0,2] for bb in body_list])[::-1] # inverted!
    body_list = [body_list[i] for i in location]
    
    #-- do detection
    #   Plan: - first make a convex hull of all centers
    #         - then see which triangles are on the edge?
    #         - make three convex hulls with only vertices of the triangle
    #           selection?
    #         - then check if vertices of other body triangles are
    #           inside any of the hulls. If they are all obscured, it's
    #           completely invisible. If not all of them, probably
    #           partially visible
    for i, front_body in enumerate(body_list[:-1]):
        keep_front = -front_body.mesh['hidden']
        if not sum(keep_front):
            continue
        for j, ecl_body in enumerate(body_list[i+1:]):
            keep_back = -ecl_body.mesh['hidden']
            front_coords = np.vstack([front_body.mesh['center'][keep_front,0:2],\
                                      front_body.mesh['triangle'][keep_front,0:2],\
                                      front_body.mesh['triangle'][keep_front,3:5],\
                                      front_body.mesh['triangle'][keep_front,6:8]])
            #front_coords = np.vstack([front_body.mesh['triangle'][keep_front,0:2],\
                                      #front_body.mesh['triangle'][keep_front,3:5],\
                                      #front_body.mesh['triangle'][keep_front,6:8]])
            ed = sp.spatial.Delaunay(front_coords)
            in_eclipse_c = ed.find_simplex(ecl_body.mesh['center'][keep_back,0:2])>=0
            in_eclipse_1 = ed.find_simplex(ecl_body.mesh['triangle'][keep_back,0:2])>=0
            in_eclipse_2 = ed.find_simplex(ecl_body.mesh['triangle'][keep_back,3:5])>=0
            in_eclipse_3 = ed.find_simplex(ecl_body.mesh['triangle'][keep_back,6:8])>=0
            #-- construct boolean arrays
            in_eclipse = np.vstack([in_eclipse_c,in_eclipse_1,in_eclipse_2,in_eclipse_3])
            sum_in_eclipse = in_eclipse.sum(axis=0)
            hidden  = sum_in_eclipse==4
            visible = sum_in_eclipse==0
            # and fill in the mesh
            ecl_body.mesh['hidden'][keep_back] = hidden
            ecl_body.mesh['visible'][keep_back] = visible
            ecl_body.mesh['partial'][keep_back] = -hidden & -visible
    #-- that's it!
    return None


#{ Graham scan + KDTree

def turn(p, q, r):
    """
    Returns -1, 0, 1 if p,q,r forms a right, straight, or left turn.
    """
    return np.sign((q[:,0] - p[:,0])*(r[:,1] - p[:,1]) - (r[:,0] - p[:,0])*(q[:,1] - p[:,1]))

def graham_scan(points):
    """
    Perform a Graham scan to find the convex hull.
    
    @param points: array of N 2-D points
    @type points: numpy array (N,2)
    @return: points on the hull, end-index of "lower" hull.
    @rtype: ndarray, int
    """
    sa = np.argsort(points[:,0], kind='heapsort')
    myhull, index0, index1 = fconvex.convex_hull(points[sa])
    return myhull[:index0], index1


def inside_hull(testpoint, hull, iturn):
    """
    Test if points or inside a convex hull.
    
    @param testpoint: array of N test points in 2D.
    @type testpoint: array of shape (N,2)
    """
    # If the test point is entirely to the left or entirely to the right of the
    # hull, it's not in there
    inside = np.ones(len(testpoint),bool)
    ends = hull[:iturn,0].searchsorted(testpoint[:,0])
    is_out = (ends==0) | (ends==iturn)
    inside[is_out] = False
    # If it is below the nearest bottom edge, it's not inside the hull
    inside[-is_out] = turn(hull[ends-1][-is_out], hull[ends][-is_out], testpoint[-is_out])==1
    # If it is above the nearest top edge, it's not inside the hull
    #return inside
    hull_ = hull[iturn-1:][::-1]
    ends = hull_[:,0].searchsorted(testpoint[:,0])
    is_out = (ends==0) | (ends==len(hull_))
    inside[-is_out] = inside[-is_out] & (turn(hull_[ends-1][-is_out], hull_[ends[-is_out]], testpoint[-is_out])==-1)
    return inside

def closest_points(hull, testpoints, distance):
    """
    Return all points in testpoints that are closer than distance from hull.
    
    @param hull: the hull
    @type hull: (k,2) numpy array
    @param testpoints: points to select from
    @type testpoints: (n,2) numpy array
    @param distance: distance tolerance for selection
    @type distance: float
    """
    tree = KDTree(testpoints)
    indices = np.unique(tree.query_ball_point(hull, distance).sum(axis=0))
    return indices
    
def convex_graham(body_list, distance_factor=1.0, first_iteration=True):
    """
    Eclipse detection via Graham scan and binary search tree.
    
    @param body_list: list of bodies
    @type body_list: list of Bodies
    """
    if not isinstance(body_list,list):
        body_list = [body_list]
    
    # Make sure some defaults are set
    #if first_iteration:
    horizon_via_normal(body_list)
    
    #body_list = system.get_bodies()
    # Order the bodies from front to back. Now I do a very crude approximation
    # that can break down once you have small body very near the surface
    # of the other body. I simply order them according to the location of
    # the first triangle in the mesh.
    location = np.argsort([bb.mesh['center'][0,2] for bb in body_list])[::-1] # inverted!
    body_list = [body_list[i] for i in location]
    min_sizes = [bb.mesh['size'].min() for bb in body_list]
    
    detected_eclipse = False
    
    for j, star2 in enumerate(body_list[:-1]):
        for i, star1 in enumerate(body_list[j+1:]):
            i = i+j+1
            # Keep track of triangles that are hidden / visible
            visible1 = -star1.mesh['hidden']
            visible2 = -star2.mesh['hidden']
            
            # If nothing is visible in the star behind, it's quite easy;
            # we will not detect anything better!
            if not np.any(visible1):
                continue
            
            # Determine a scale factor for the triangle
            distance = distance_factor * 2.0/3**0.25*np.sqrt(min_sizes[i])
            
            # Select only those triangles that are not hidden
            front = np.vstack([star2.mesh['triangle'][visible2,0:2],
                                star2.mesh['triangle'][visible2,3:5],
                                star2.mesh['triangle'][visible2,6:8]])
            back = np.vstack([star1.mesh['triangle'][visible1,0:2],
                                star1.mesh['triangle'][visible1,3:5],
                                star1.mesh['triangle'][visible1,6:8]])

            # Star in front ---> star in back
            if not front.shape[0]:
                continue
            hull, iturn = graham_scan(front)
            inside = inside_hull(back, hull, iturn)
            
            hidden = inside.reshape(3,-1).all(axis=0)
            arg = np.where(visible1)[0][hidden]
            star1.mesh['hidden'][arg] = True
            star1.mesh['visible'][arg] = False
            star1.mesh['partial'][arg] = False
            
            visible = -(inside.reshape(3,-1).any(axis=0))
            arg = np.where(visible1)[0][visible]
            star1.mesh['visible'][arg] = True
            star1.mesh['hidden'][arg] = False
            star1.mesh['partial'][arg] = False | star1.mesh['partial'][arg]
            
            # Triangles that are partially hidden are those that are not
            # completely hidden, but do have at least one vertex hidden
            partial = -hidden & -visible
            
            arg = np.where(visible1)[0][partial]
            star1.mesh['visible'][arg] = False
            star1.mesh['partial'][arg] = True
            if np.any(partial):
                detected_eclipse = True
            
            
            # It's possible that some triangles that do not have overlapping
            # vertices, still are partially covered (i.e. if the objects fall
            # in between the vertices)
            visible1 = -star1.mesh['hidden']
            backc = star1.mesh['center'][visible1,0:2]
            if not len(backc):
                continue
            
            subset_partial = closest_points(hull, backc, distance)
            
            if not len(subset_partial):
                continue
            
            arg = np.where(visible1)[0][subset_partial]
            star1.mesh['visible'][arg] = False
            star1.mesh['partial'][arg] = True
            detected_eclipse = True
                        
    return True










    
#{ Retrieving obstructed rays    
    
def ray_triangle_intersection(ray,triangle):
    """
    Compute intersection between a ray and a triangle.
    
    Return flag is:

    * -1 if triangle is degenerate
    *  0 if ray does not intersect plane
    * +1 if ray intersects plane
    * +2 if ray lies in triangle plane
    
    @param ray: 2 points defining the ray
    @type ray: tuple ( ndarray(3), ndarray(3) )
    @param triangle: triangle to intersect
    @type triangle: 3 vertices defining the triangle
    @param triangle: ndarray(9), (x1,y1,z1,x2,y2,z2,x3,y3,z3)
    @return: flag
    @rtype: int
    """
    V0 = triangle[0:3]
    V1 = triangle[3:6]
    V2 = triangle[6:9]
    P0 = ray[0]
    P1 = ray[1]
    
    #-- get triangle edge vectors and plane normal
    u = V1-V0
    v = V2-V0
    n = np.cross(u,v)
    #-- test if triangle is degenerate
    if np.all(n==0):
        return -1
    
    #-- ray direction
    dir = P1-P0
    w0 = P0-V0
    a = -np.dot(n,w0)
    b =  np.dot(n,dir)
    #-- test if ray is parallel to triangle plane
    if np.allclose(np.abs(b),0):
        if a==0: # ray lies in triangle plane
            return 2
        else:    # ray disjoint from plane
            return 0
    
    #-- get intersect point of ray with triangle plane
    r = a/b
    if r<0: return 0 # ray goes away from triangle, no intersect
    I = P0 + r*dir # intersect point of ray and plane
    
    #-- is I inside T?
    uu = np.dot(u,u)
    uv = np.dot(u,v)
    vv = np.dot(v,v)
    w = I-V0
    wu = np.dot(w,u)
    wv = np.dot(w,v)
    D = uv * uv - uu*vv
    
    # get and test parameteric coords
    s = (uv*wv-vv*wu)/D
    if (s < 0.0 or s > 1.0):#        // I is outside T
        return 0
    t = (uv * wu - uu * wv) / D
    if (t < 0.0 or (s + t) > 1.0):#  // I is outside T
        return 0

    return 1#                      // I is in T

    
def get_obstructed_los(center0,centers1,third_bodies):
    """
    Return lines-of-sight that are obstructed by third bodies.
    
    @param center0: origin of all lines of sight
    @type center0: ndarray(3)
    @param centers1: end points of the line of sights
    @type centers1: Nx3 array
    @param third_bodies: Body that could be obstructing the lines of sight
    @type third_bodies: Body
    @return: boolean array listing the lines-of-sight that are obstructed
    @rtype: boolean array (ndarray(N))
    """
    obstructed = np.zeros(len(centers1),bool)
    for i,center1 in enumerate(centers1):
        for j,triangle in enumerate(third_bodies.mesh['triangle']):
            obstr = ray_triangle_intersection((center0,center1),triangle)
            if obstr:
                obstructed[i] = True
                break
    return obstructed
    
#}