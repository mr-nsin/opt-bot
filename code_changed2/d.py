import threading
import time

# Define a flag to signal the threads to exit
exit_flag = False

# Function to be executed by the first thread
def thread_function_1():
    if not exit_flag:
        print("Thread 1 is running")
        time.sleep(1)

# Function to be executed by the second thread
def thread_function_2():
    if not exit_flag:
        
        print("Thread 2 is running")
        time.sleep(1)

# Create two threads
thread_1 = threading.Thread(target=thread_function_1)
thread_2 = threading.Thread(target=thread_function_2)

# Start the threads
thread_1.start()
thread_2.start()

# Wait for a while (or perform some other tasks)
time.sleep(5)

# Set the exit_flag to signal threads to exit
exit_flag = True

# Wait for both threads to complete
thread_1.join()
thread_2.join()

print("Both threads have exited")
