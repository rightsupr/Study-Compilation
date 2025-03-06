# **freeRTOS**

以上就是rtos的简单理解

## 堆栈

### 堆

与栈相比是程序员所规定划分出的一块内存

```python
char heap_buf[1024];
```

``` int* p = (int*)malloc(4);
int* p = (int*)malloc(4);
//int* 表示“指向 int 类型数据的指针 ,p 是一个变量，它保存的是“某个 int 类型数据在内存中的地址
= (int*)malloc(4); //malloc(4) 会向操作系统请求 4 个字节的连续内存空间
```

使用后需要释放内存 free(p);

```
p = (int*)calloc(4, 1);
//calloc(4, 1) 会分配 4 字节的连续内存，并且将这 4 字节初始化为 0。它与 malloc 的区别主要在于，calloc 会在分配内存后自动将其清零。
//若要分配4个int，一般会用 calloc(4, sizeof(int))
```





### 栈

与堆相比，是不被程序员所规定的

![栈1](image/栈1.png)

main 程序运行到a_fun(46)之前，会先将return 0的地址保存到LR（LinkRegister）中，然后调用函数a_fun(), 

同样的，进入到a_fun()中，也会调用b_fun()。在执行之前，也会保存一遍c_fun()的地址进入LR。

`那么问题来了，都保存LR，那岂不是重叠覆盖了? `    这就提到了栈的用处

再上面的基础上，会把LR存入栈中（例如即将执行a_fun()，就会先把return 0的地址存入为a_fun()所划分出的栈）如下图

**栈就是一块空闲的内存**

![栈2](image/栈2.png)





# 任务

## rtos的实现从代码上的理解

![image.png](attachment:9f0b573c-b72f-4b19-b1d8-6e0dd8b48c95:image.png)

运行任务A到B，再回到A：任务A可能运行到一半即是“stop”就暂停了，这要求需要保存很多东西

1、执行的位置（因为要恢复执行）

2、变量的值，不能被破坏了

故，什么是任务，就是 运行中的函数

保存的就是：代码、运行位置、**运行环境**

### [函数运行的环境：](https://www.notion.so/ARM-19f059b7336d80b88891d6a0f8888a7b?pvs=21)

跳转，从底层的arm架构理解，知道cpu、ram、flash之间的关系，再了解汇编语言，知道任务切换时候，是把寄存器里的值全部保存到栈里

## 创建任务函数简析

### 任务的三个核心：

函数、栈（一块空闲的内存）、任务结构体（怎么找到这些栈）

![image.png](attachment:314eb546-b15e-4eb8-b24f-a3931d6ac6a1:image.png)

![image.png](attachment:137f5e8f-bb59-48d0-b1e4-64aa377b3036:image.png)

最下面的就是TCB结构体，至少包含：fun、sp、优先级、name、参数

### 创建任务的内部细节：

栈大小取决于：1、局部变量；2、调度深度

freertos是直接取了一个17k的内存用于动态内存分配，即从一个巨大的数组里划分一个内存给某个任务用作栈

![image.png](attachment:649b79d9-1fb4-4f27-b684-069ca5dba9c9:image.png)

![image.png](attachment:aff1e751-0fc3-4eb2-8374-97a53012dd6e:image.png)

vTask1这个函数指针就是这个地址，所以要去执行这个函数就是要把这个地址赋给PC寄存器

函数的参数是放在R0里

![image.png](attachment:a4b0f352-6d4f-4826-bc21-7dda6c66d9fd:image.png)

其中这个1000就是1000*4的大小会去巨大的数组划分空间

这个空间的起始地址为下面的任务结构体的pxStack

![image.png](attachment:655e53c6-18c0-4b20-a092-2cb208a7f4fb:image.png)

所以创建任务实际就是刚刚说的从分配的内存里从R15（PC）往下（高位）生长，并保存寄存器

第一次创建就像是保存了一次现场。1000*4就是刚刚分配的内存（这边pxStack的位置可能不对，有可能在下面。关于高地址在上在下）

![image.png](attachment:822dec20-eb05-4df1-8abb-5f122373915e:image.png)

### 任务调度机制

**优先级不同：**高优先级的任务优先执行，可以抢占低优先级的任务

高优先级的不停止，低优先级的永远不执行

同等任务级的任务轮流执行：“时间片轮转”

**状态：**

运行态

就绪态

阻塞：等待某件事（时间）     本来我想去做的，但是我得等

挂起              休息去了，不是因为等

**怎么管理？**

怎么取出要运行的任务：找到最高优先级的运行态、就绪态，运行它；如果平级，轮流运行，即排队，链表前面的先运行，运行1个tick后乖乖去链表尾部排队

![image.png](attachment:47b924e8-ecb9-4973-a5c9-20db9ca41e80:image.png)

如图就是任务分别被放在readylist 任务1 2放在pxReadyTasksLists[0],task3放在2.于是选出可以执行的程序就很简单，从链表4开始往下找，然后找到链表2有任务，于是拿出来执行。任务2进入了5ms的延迟，进入pxDelayedTaskList，每个tick都会刷新一次链表。当task3在休息时，tick找到链表0，看到task1，执行。执行完后把他放到后面去，再执行task2，执行完也放在后面。直到task3休息完，由进入执行，如此往复循环。

关于**就序列表怎么排列**的：创建后放入的任务要是同优先级，当前任务就变为后任务（即TCB指向后任务）。要是后任务是高优先级，当前任务也变为后任务，否则还是前任务

![image.png](attachment:9f717388-f9e9-4570-adfb-24d514a81f86:image.png)

**谁进行调度？**

tick中断 （每隔固定时间的定时器中断）在freertos就是1ms

tick中断函数就要做：1、取出下一个Task；2、切换任务（保存当前，恢复新任务）

![image.png](attachment:3c2f6a82-b354-4c29-9110-d339c1cb430f:image.png)

更详细的调度：

在创建main的时候，最下面启动了调度器

![image.png](attachment:e9ceef6f-63ca-4f8a-8579-d92bc1d9ac29:image.png)

在调度器里实际上创建了一个空闲任务，优先级也是0，作用主要是清理工作。例如，任务1自杀了，他的栈由空闲任务来释放

![image.png](attachment:60c4a303-6a4e-40bb-91a3-3f7adc93e74c:image.png)

### 通过链表深入理解调度机制

```
     可抢占：高优先级的任务先运行

     时间片轮转：同优先级的任务轮流执行

     空闲任务礼让：如果有同是优先级0的就绪任务，空闲任务主动放弃一次运行机会（空闲是0）
```

ps：任何硬件中断优先级都高于rtos的优先级

### rtos任务调度机制的总体思路理解

任务1和任务2同时执行，通过tick中断实现切换任务，即（1、找出优先级最高的任务；2、去执行）

关于**找出优先级最高的任务，就要知道去哪找———-知道链表就很简单**

RTOS有三类链表，对于第一类又有很多个链表。他从上往下找并执行，并任务放在同优先级的最后。每一次tick找一次。

![image.png](attachment:b672b722-daf7-4404-9955-928204d7eba9:image.png)

## 深入理解RTOS的队列及队列的实战

### 两个人任务单独执行，但是数据要交互，该怎么办

如下图，同时运行任务1和任务2，都是以同样的方式a++，但是假设在运行过程中，第一个tick，任务1执行，但是停在了读取a的值或者修改R0的值，没有完成最后一步把R0的值写入a，立马执行了任务2，两个任务都执行完最终a=1，并非理想的等于2。虽然马上又恢复现场再执行任务1

![image.png](attachment:aa9ffe6b-a362-4f60-ab87-b36e1b8cc131:image.png)

这就要求引入很多的机制，保证整个数据不被破坏

多任务访问同一个变量的时候就要**考虑互斥**的问题。如果任务1在访问变量a的时候可以互斥地访问就可以解决

这就要通过队列来实现

### 队列

#### 队列的实现与第一个好处

就上面的例子而言，那我是不是可以不让多人写。

有的xd，有的。引入一个环形缓冲区

![队列1](image/队列1.png)

进队列，就是进队列函数了

![队列2](image/队列2.png)

比如任务a，进入队列函数，如何先关闭中断，大家都不许运行了，变成好像裸机开发了，然后做完后，开中断

![队列3](image/队列3.png)

队列操作函数不用自己写，直接掉调用这个写队列函数就行了

#### 队列的第二个好处

休眠唤醒机制，就是下面提到的队列[阻塞访问](#阻塞访问)

当写队列的时候，除了要写数据，还要Wake up

怎么Wake up呢？就是从Queue.list中去唤醒

是由于，比如读数据的时候发现队列是空的，那么就要要休眠，不仅仅是把自己这个任务从ReadyList移动到DelayList里，还要把自己放在Queue.list里，这样其他的任务列入写数据的时候才知道唤醒他。

消息队列**核心：关中断、链表操作、环形缓冲区**

环形缓冲区就是读写都有个指针，比如写就是下面的方法

```c 
buf[w]=val;
w=(w+1)%len
```

通过这种方式，每次到走到队尾，又会回到队头，实现**先进先出**

这就是下面提到的数据存储的核心

#### 数据储存

一个队列能保存有限数量的固定大小的数据单元。一个队列能保存单元的最大数量叫做 “长度”。每个队列数据单元的长度与大小是在创建队列时设置的。队列通常是一个先入先出（[FIFO](https://so.csdn.net/so/search?q=FIFO&spm=1001.2101.3001.7020)）的环形缓冲区

#### 传输数据的两种方法

- 拷贝：把数据、把变量的值复制进队列里
- 引用：把数据、把变量的地址复制进队列里

#### 队列的阻塞访问

<a id="阻塞访问"></a>

就比如当读取空队列，发现没数据，读写不成功，就阻塞。这其中可以指定超时时间；同样的，当队列满了，写入失败了，也会阻塞，同样可以指定超时时间。

以读取队列为例，如果队列有数据了，则该阻塞的任务会变为就绪态。**如果一直都没有数据，则时间到之后它也会进入就绪态。**

` 那么，既然已经有一种方式，即“队列有数据就进入就绪态”还需要超时时间干嘛? `

 答：避免任务长时间“死等”,系统可以做一些其他的处理方式，例如重新初始化，或者提醒开发者作排查

`那么，如果队列中有数据后，谁会优先进入就绪态呢？`  

1、优先级最高的任务

2、如果优先级一样，则等待时间最久的任务先进入就绪态

#### 队列函数：

##### 创建

分为动态分配内存、静态分配内存

动态分配内存：`xQueueCreate` 队列的内存在函数内部动态分配

```c
QueueHandle_t xQueueCreate( UBaseType_t uxQueueLength, UBaseType_t uxItemSize );
```

静态分配内存：`xQueueCreateStatic`，队列的内存要事先分配好

```c
QueueHandle_t xQueueCreateStatic(
							UBaseType_t uxQueueLength,
							UBaseType_t uxItemSize,
							uint8_t *pucQueueStorageBuffer,
							StaticQueue_t *pxQueueBuffer
						);
```

​        **复位**      队列刚被创建时，里面没有数据；使用过程中可以调用 xQueueReset() 把队列恢复为初始状态，此函数原型为：

``` c
BaseType_t xQueueReset( QueueHandle_t pxQueue);
```

##### 删除

删除队列的函数为 `vQueueDelete()` ，只能删除使用**动态方法**创建的队列，它会释放内存

``` c
void vQueueDelete( QueueHandle_t xQueue );
```

##### 写队列

可以把数据写到队列头部，也可以写到尾部。较为普遍的使用是下面的xQueueSend()   *往队列尾部写入数据*

``` c
BaseType_t xQueueSend(
				QueueHandle_t xQueue,
				const void *pvItemToQueue,
				TickType_t xTicksToWait
			);
```

另外xQueueSendToBack  xQueueSendToBackFromISR  xQueueSendToFront  xQueueSendToFrontFromISR

##### 读队列

使用 `xQueueReceive()` 函数读队列，读到一个数据后，队列中该数据会被**移除**。

```c
BaseType_t xQueueReceive( QueueHandle_t xQueue,
					void * const pvBuffer,
					TickType_t xTicksToWait );

BaseType_t xQueueReceiveFromISR(
							QueueHandle_t xQueue,
							void *pvBuffer,
							BaseType_t *pxTaskWoken
						);
```

##### 查询

可以查询队列中有多少个数据、有多少空余空间。

``` c
* 返回队列中可用数据的个数
UBaseType_t uxQueueMessagesWaiting( const QueueHandle_t xQueue );
* 返回队列中可用空间的个数
UBaseType_t uxQueueSpacesAvailable( const QueueHandle_t xQueue );
```

##### 覆盖/偷看

这与上面的读队列的方法不同，偷看的方法实现了多方数据共享，都可以读这个队列，所以读完不删除数据。

```c 
/* 覆盖队列
* xQueue: 写哪个队列
* pvItemToQueue: 数据地址
* 返回值: pdTRUE表示成功, pdFALSE表示失败
*/
BaseType_t xQueueOverwrite(
					QueueHandle_t xQueue,
					const void * pvItemToQueue
				);

BaseType_t xQueueOverwriteFromISR(
							QueueHandle_t xQueue,
							const void * pvItemToQueue,
							BaseType_t *pxHigherPriorityTaskWoken
						);
```

但是由于不删除数据，如果不做处理，就会导致队列数据阻塞，导致发送任务进入阻塞状态。

应对措施：

1、定期清理队列数据，使用receive移除已经被窥看过的数据。

2、动态调整队列长度，通过`uxQueueSpacesAvailable()`可以随时监控队列的可用空间，动态调整运行逻辑

3、限制窥视操作，可以通过逻辑控制确保窥视的频率低于数据移除的频率。

4、采用事件通知（task notification）或直接共享内存区域，不完全依赖队列的方法
