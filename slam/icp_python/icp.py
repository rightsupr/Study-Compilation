import numpy as np
import matplotlib.pyplot as plt
from sklearn.neighbors import KDTree


def visualize_registration(source, target, transformed, iteration, rmse):
    """3D visualization of registration progress with multiple views"""
    fig = plt.figure(figsize=(15, 5))
    
    # 3D View
    ax1 = fig.add_subplot(131, projection='3d')
    ax1.scatter(source[0], source[1], source[2], c='r', marker='o', s=5, label='Source')
    ax1.scatter(target[0], target[1], target[2], c='b', marker='^', s=5, label='Target')
    ax1.scatter(transformed[0], transformed[1], transformed[2], c='g', marker='x', s=5, label='Transformed')
    ax1.set_title(f'Iteration: {iteration}\nRMSE: {rmse:.6f}')
    ax1.legend()
    
    # XY Projection
    ax2 = fig.add_subplot(132)
    ax2.scatter(source[0], source[1], c='r', s=3)
    ax2.scatter(target[0], target[1], c='b', s=3)
    ax2.scatter(transformed[0], transformed[1], c='g', s=3)
    ax2.set_aspect('equal')
    ax2.set_title('XY Plane')
    
    # XZ Projection
    ax3 = fig.add_subplot(133)
    ax3.scatter(source[0], source[2], c='r', s=3)
    ax3.scatter(target[0], target[2], c='b', s=3)
    ax3.scatter(transformed[0], transformed[2], c='g', s=3)
    ax3.set_aspect('equal')
    ax3.set_title('XZ Plane')
    
    plt.tight_layout()
    plt.savefig(f'iteration_{iteration:03d}.png')
    plt.close()

def IterativeClosestPoint(source_pts, target_pts, tau=1e-6, max_iter=100, visualize=False):
    '''
    This function implements iterative closest point algorithm based 
    on Besl, P.J. & McKay, N.D. 1992, 'A Method for Registration 
    of 3-D Shapes', IEEE Transactions on Pattern Analysis and Machine 
    Intelligence, vol. 14, no. 2,  IEEE Computer Society. 

    inputs:
    source_pts : 3 x N
    target_pts : 3 x M
    tau : threshold for convergence
    Its the threshold when RMSE does not change comapred to the previous 
    RMSE the iterations terminate. 

    outputs:
    R : Rotation Matrtix (3 x 3)
    t : translation vector (3 x 1)
    k : num_iterations
    '''

    # Input validation
    assert source_pts.shape[0] == 3, "Source points must be 3xN array"
    assert target_pts.shape[0] == 3, "Target points must be 3xM array"
    
    # Data normalization
    source_pts = source_pts / np.max(np.abs(source_pts))
    target_pts = target_pts / np.max(np.abs(target_pts))
    
    k = 0
    current_pts = source_pts.copy()
    last_rmse = float('inf')
    R = np.eye(3)
    t = np.zeros((3, 1))
    
    # Precompute target normals for point-to-plane
    target_normals = compute_normals(target_pts)
    
    # Visualization setup
    if visualize:
        plt.ioff()  # Non-interactive mode
        visualize_registration(source_pts, target_pts, source_pts, 0, 0)

    while k < max_iter:
        # Find correspondences with distance threshold
        neigh_pts, valid_indices = find_valid_correspondences(current_pts, target_pts)
        
        if len(valid_indices) < 3:  # Minimum 3 points for SVD
            break
            
        # Point-to-plane registration
        R, t = register_points_plane(current_pts[:, valid_indices], 
                                   neigh_pts, 
                                   target_normals)
        
        # Apply transformation
        current_pts = ApplyTransformation(source_pts, R, t)
        rmse = ComputeRMSE(current_pts[:, valid_indices], neigh_pts)
        
        # Visualization
        if visualize:
            visualize_registration(source_pts, target_pts, current_pts, k+1, rmse)
            
        # Convergence check
        if abs(rmse - last_rmse) < tau and k > 5:
            break
            
        last_rmse = rmse
        k += 1

    return (R, t, k)


# Computes the root mean square error between two data sets.
# here we dont take mean, instead sum.
def ComputeRMSE(p1, p2):
    return np.sum(np.sqrt(np.sum((p1-p2)**2, axis=0)))


# applies the transformation R,t on pts
def ApplyTransformation(pts, R, t):
    return np.dot(R, pts) + t

# applies the inverse transformation of R,t on pts
def ApplyInvTransformation(pts, R, t):
    return np.dot(R.T,  pts - t)

# calculate naive transformation errors
def CalcTransErrors(R1, t1, R2, t2):
    Re = np.sum(np.abs(R1-R2))
    te = np.sum(np.abs(t1-t2))
    return (Re, te)


# point cloud registration between points p1 and p2
# with 1-1 correspondance
def RegisterPoints(p1, p2):
    u1 = np.mean(p1, axis=1).reshape((3, 1))
    u2 = np.mean(p2, axis=1).reshape((3, 1))
    pp1 = p1 - u1
    pp2 = p2 - u2
    W = np.dot(pp1, pp2.T)
    U, _, Vh = np.linalg.svd(W)
    R = np.dot(U, Vh).T
    if np.linalg.det(R) < 0:
        Vh[2, :] *= -1
        R = np.dot(U, Vh).T
    t = u2 - np.dot(R, u1)
    return (R, t)


# function to find source points neighbors in
# target based on KDTree
def compute_normals(points, k=10):
    """Estimate normals using PCA on k-nearest neighbors"""
    kdt = KDTree(points.T)
    normals = np.zeros(points.shape)
    
    for i in range(points.shape[1]):
        _, idx = kdt.query(points[:,i:i+1].T, k=k)
        neighbors = points[:, idx.ravel()]
        cov = np.cov(neighbors)
        U, S, _ = np.linalg.svd(cov)
        normals[:,i] = U[:,-1]  # Smallest principal component
        
    return normals / np.linalg.norm(normals, axis=0)

def find_valid_correspondences(source, target, max_dist=0.1):
    """Find correspondences with distance thresholding"""
    kdt = KDTree(target.T)
    dist, idx = kdt.query(source.T, k=1, return_distance=True)
    valid = dist.ravel() < max_dist
    return target[:, idx[valid].ravel()], np.where(valid)[0]

def register_points_plane(source, target, target_normals):
    """Point-to-plane registration using SVD"""
    # Build linear system
    C = target_normals.T
    A = np.zeros((source.shape[1]*3, 6))
    b = np.zeros(source.shape[1]*3)
    
    for i in range(source.shape[1]):
        sx = source[:,i]
        tx = target[:,i]
        n = C[i]
        skew = np.array([[0, -sx[2], sx[1]],
                         [sx[2], 0, -sx[0]],
                         [-sx[1], sx[0], 0]])
        A[3*i:3*i+3, :3] = skew
        A[3*i:3*i+3, 3:] = np.eye(3)
        b[3*i:3*i+3] = (tx - sx) * n
    
    # Solve linear system
    x, _, _, _ = np.linalg.lstsq(A, b, rcond=None)
    alpha, beta, gamma = x[:3]
    t = x[3:]
    
    # Convert to rotation matrix
    R = np.array([[1, -gamma, beta],
                  [gamma, 1, -alpha],
                  [-beta, alpha, 1]])
    U, _, Vt = np.linalg.svd(R)
    R = U @ Vt
    
    return R, t.reshape(3,1)
