import numpy as np
import matplotlib.pyplot as plt
from scipy.spatial import KDTree
from matplotlib.animation import FuncAnimation

class ICP:
    def __init__(self, max_iterations=50, tolerance=0.001):
        self.max_iter = max_iterations
        self.tolerance = tolerance
        self.errors = []
        
    def fit(self, source, target):
        self.src = source.copy()
        self.dst = target.copy()
        
        fig, (self.ax1, self.ax2) = plt.subplots(1, 2, figsize=(12, 6))
        self.setup_plot()
        
        transformation = np.eye(3)
        
        for i in range(self.max_iter):
            # 最近邻搜索
            distances, indices = self.nearest_neighbor(self.src, self.dst)
            
            # 计算变换矩阵
            T = self.calculate_transform(self.src, self.dst[indices])
            
            # 应用变换
            self.src = self.apply_transform(self.src, T)
            transformation = T @ transformation
            
            # 计算误差
            mean_error = np.mean(distances)
            self.errors.append(mean_error)
            
            # 更新绘图
            self.update_plot(i, transformation)
            
            # 检查收敛
            if len(self.errors) > 1 and abs(self.errors[-2] - self.errors[-1]) < self.tolerance:
                break
                
        plt.show()
        return transformation
    
    def nearest_neighbor(self, src, dst):
        tree = KDTree(dst)
        distances, indices = tree.query(src, k=1)
        return distances, indices
    
    def calculate_transform(self, src, dst):
        # 计算质心
        src_centroid = np.mean(src, axis=0)
        dst_centroid = np.mean(dst, axis=0)
        
        # 去中心化
        src_centered = src - src_centroid
        dst_centered = dst - dst_centroid
        
        # 计算旋转矩阵
        H = src_centered.T @ dst_centered
        U, _, Vt = np.linalg.svd(H)
        R = Vt.T @ U.T
        
        # 计算平移向量
        t = dst_centroid - R @ src_centroid
        
        # 构造齐次变换矩阵
        T = np.eye(3)
        T[:2, :2] = R
        T[:2, 2] = t
        return T
    
    def apply_transform(self, points, T):
        # 添加齐次坐标
        homo_points = np.hstack([points, np.ones((points.shape[0], 1))])
        return (homo_points @ T.T)[:, :2]
    
    def setup_plot(self):
        self.ax1.clear()
        self.ax1.scatter(self.src[:,0], self.src[:,1], c='r', label='Source')
        self.ax1.scatter(self.dst[:,0], self.dst[:,1], c='b', label='Target')
        self.ax1.set_title('Initial Position')
        self.ax1.legend()
        self.ax1.axis('equal')
        
        self.ax2.clear()
        self.line, = self.ax2.plot([], 'g-', lw=2)
        self.ax2.set_xlim(0, self.max_iter)
        self.ax2.set_ylim(0, np.max(self.errors) if self.errors else 1)
        self.ax2.set_title('Registration Process')
        self.ax2.set_xlabel('Iteration')
        self.ax2.set_ylabel('Error')
    
    def update_plot(self, iteration, T):
        self.ax1.clear()
        self.ax1.scatter(self.src[:,0], self.src[:,1], c='#FF00FF', s=5, alpha=0.6, marker='.', edgecolors='none', label='Transformed Source')
        self.ax1.scatter(self.dst[:,0], self.dst[:,1], c='#00FFFF', s=5, alpha=0.6, marker='.', edgecolors='none', label='Target')
        self.ax1.set_title(f'Iteration {iteration+1}\nTransformation Matrix:\n{np.round(T, 3)}')
        self.ax1.legend()
        self.ax1.axis('equal')
        
        self.line.set_data(np.arange(len(self.errors)), self.errors)
        self.ax2.relim()
        self.ax2.autoscale_view()
        plt.pause(0.5)

def generate_room_point_cloud(length=6.0, width=4.0, height=2.5, 
                             points_per_wall=100, noise=0.02):
    """生成矩形房间点云"""
    # 生成墙面点
    walls = []
    
    # 地面和天花板（添加z坐标）
    x = np.linspace(0, length, points_per_wall)
    z = np.linspace(0, height, points_per_wall//2)
    for y in [0, width]:
        for xi in x:
            for zi in z:
                walls.append([xi, y, zi])
    
    # 左右墙面
    y = np.linspace(0, width, points_per_wall)
    for x in [0, length]:
        for yi in y:
            for zi in z:
                walls.append([x, yi, zi])
    
    # 添加门框（宽1m，高2m）
    door_y = np.linspace(width/2-0.5, width/2+0.5, 20)
    door_z = np.linspace(0, 2.0, 40)
    for dy in door_y:
        for dz in door_z:
            walls.append([0, dy, dz])  # 在x=0墙面
    
    # 添加窗户（宽1.5m，高1m）
    window_x = np.linspace(length/2-0.75, length/2+0.75, 30)
    window_z = np.linspace(1.0, 2.0, 20)
    for wx in window_x:
        for wz in window_z:
            walls.append([wx, width, wz])  # 在y=width墙面
    
    # 转换为numpy数组并添加噪声
    points = np.array(walls)
    points += np.random.normal(0, noise*3, points.shape)
    
    # 添加三维随机点增加密度
    extra_points = np.random.uniform(
        low=[0, 0, 0],
        high=[length, width, height],
        size=(points_per_wall*2, 3)
    )
    points = np.vstack([points, extra_points])
    
    # 添加表面噪声点
    surface_noise = np.random.uniform(
        low=[-0.1, -0.1, -0.1],
        high=[0.1, 0.1, 0.1],
        size=(points_per_wall, 3)
    )
    points = np.vstack([points, surface_noise + points[np.random.choice(len(points), points_per_wall)]])
    
    # 投影到二维（忽略z坐标）
    return points[:, :2]

if __name__ == "__main__":
    # 生成房间点云
    np.random.seed(45)
    
    # 目标点云（基准房间）
    target = generate_room_point_cloud(points_per_wall=150, noise=0.01)
    
    # 对源点云施加初始变换（添加旋转和平移）
    angle = np.deg2rad(25)
    R = np.array([[np.cos(angle), -np.sin(angle)],
                  [np.sin(angle), np.cos(angle)]])
    t = np.array([2.3, -1.8])
    source = generate_room_point_cloud(points_per_wall=150, noise=0.01) @ R.T + t
    
    # 运行ICP
    icp = ICP(max_iterations=30, tolerance=0.0001)
    T = icp.fit(source, target)
