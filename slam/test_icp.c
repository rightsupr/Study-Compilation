#include "icp.h"
#include <stdio.h>
#include <time.h>

void generate_noise_data(ICP_Data* data, int num_points) {
    srand(time(NULL));
    for(int i=0; i<num_points; i++) {
        data->points[i].x = (rand()%1000)/1000.0 * 0.1;
        data->points[i].y = (rand()%1000)/1000.0 * 0.1;
        data->points[i].z = (rand()%1000)/1000.0 * 0.1;
    }
    data->count = num_points;
}

int main() {
    ICP_Data source, target;
    const int INIT_SIZE = 50;

    // 初始化测试数据
    icp_init(&source, INIT_SIZE);
    icp_init(&target, INIT_SIZE);
    generate_noise_data(&source, 60); // 测试动态扩展
    generate_noise_data(&target, 60);

    // 执行ICP算法
    Matrix3x3 R;
    Vector3D t;
    double error = compute_transform(&R, &t, source.points, target.points, source.count);

    printf("ICP误差值: %f\n", error);
    return 0;
}