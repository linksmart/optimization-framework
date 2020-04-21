import datetime
import shlex
import subprocess
from treelib import Node, Tree

class UtilFunctions:

    @staticmethod
    def get_sleep_secs(repeat_hour, repeat_min, repeat_sec, min_delay=10):
        current_time = datetime.datetime.now()
        repeat_sec = repeat_hour*3600 + repeat_min*60 + repeat_sec
        if repeat_sec <= min_delay:
            return min_delay
        start_of_day = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
        seconds_since_start_of_day = (current_time - start_of_day).total_seconds()
        sec_diff = repeat_sec - seconds_since_start_of_day%repeat_sec
        if sec_diff < min_delay:
            sec_diff = min_delay
        return int(sec_diff)

    @staticmethod
    def execute_command(command, service_name, msg):
        try:
            command = shlex.split(command)
            print("command "+str(command))
            process = subprocess.Popen(command, shell=False, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT)
            out, err = process.communicate()
            pid = process.pid
            print(service_name + " " + msg + " , pid = " + str(pid))
            print("Output: "+str(out.decode('utf-8')))
            print("Error: " + str(err))
            return str(out.decode('utf-8'))
        except Exception as e:
            print("error running the command " + str(command) + " " + str(e))
            return None

    @staticmethod
    def add_child_process_to_tree(tree, root, data):
        if root in data.keys():
            kids = data[root]
            for kid in kids:
                tree.create_node(kid, kid, parent=root)
                UtilFunctions.add_child_process_to_tree(tree, kid, data)

    @staticmethod
    def get_pids_to_kill_from_docker_top(number_of_gunicorn_workers, number_of_process_pool):
        try:
            command_to_write = "docker top ofw"
            output = UtilFunctions.execute_command(command_to_write, "top", "test")
            if output is not None:
                outputs = output.split("\n")
                parent_child = {}
                parents = {""}
                childs = {""}
                for i, line in enumerate(outputs):
                    if i == 0:
                        continue
                    lines = line.split(" ")
                    new_lines = []
                    for value in lines:
                        if len(value) != 0:
                            new_lines.append(value)
                    if len(new_lines) > 6:
                        if "?" in new_lines[5]:
                            print(new_lines)
                            child = new_lines[1]
                            parent = new_lines[2]
                            parents.add(parent)
                            childs.add(child)
                            if parent not in parent_child.keys():
                                parent_child[parent] = []
                            parent_child[parent].append(child)
                parents.remove("")
                childs.remove("")

                inter = parents.intersection(childs)
                for i in inter:
                    parents.remove(i)

                parents = list(parents)

                tree = Tree()
                for parent in parents:
                    tree.create_node(parent, parent)  # root

                UtilFunctions.add_child_process_to_tree(tree, parents[0], parent_child)
                print(tree.show())

                root_pid = tree.root
                ofw_pid = tree.children(root_pid)[0].tag
                gunicorn_master_pid = tree.children(ofw_pid)[0].tag

                pids = [root_pid, ofw_pid, gunicorn_master_pid]
                pids_instance = {}
                ctr = 0
                instance_number = 0
                for i, child in enumerate(tree.children(gunicorn_master_pid)):
                    if i < number_of_gunicorn_workers:
                        pids.append(child.tag)
                    else:
                        if ctr < number_of_process_pool:
                            if instance_number not in pids_instance.keys():
                                pids_instance[instance_number] = []
                            pids_instance[instance_number].append(child.tag)
                            ctr += 1
                        else:
                            ctr = 0
                            instance_number += 1
                print("root and swagger pids "+str(pids))
                all_pids = pids.copy()
                for pid in pids_instance.values():
                    all_pids.extend(pid)
                rest_pids = UtilFunctions.get_rest_pids(tree, all_pids)
                return pids, pids_instance, rest_pids
        except Exception as e:
            print("exception getting pids "+str(e))
            return None, None, None

    @staticmethod
    def get_rest_pids(tree, pids):
        try:
            other_pids = []
            for node in tree.all_nodes_itr():
                tag = node.tag
                if tag not in pids:
                    other_pids.append(tag)
            return other_pids
        except Exception as e:
            print("error "+str(e))