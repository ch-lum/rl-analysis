import json
import numpy as np

class PhysPar:
    GOAL_Y = 510000
    PHYS_ID = 42
    COLOR_ID = 66
    TEAM_SIZE = 3

    def __init__(self, fp):
        self.fp = fp
        with open(self.fp, "r") as json_file:
            self.data = json.load(json_file)
        self.update_frames = [x['frame'] for x in self.data['content']['body']['key_frames']]
        self.physics = self.get_physics()

    def get_spawnframe(self, frame):
        '''
        Returns the appropriate spawnframe for a given frame

        :param frame: int of a frame
        '''
        if not isinstance(frame, int):
            raise ValueError('frame must be an integer')
        if frame < 0:
            raise ValueError('frame must be greater than 0')
        
        return max([x for x in self.update_frames if x <= frame])
    
    def find_ids(self, spawnframe=0):
        '''
        This function returns a dictionary of all the IDs for a given spawn cycle
        Important for finding 'TAGame.Car_TA' and 'TAGame.Ball_TA'

        :param spawnframe: int, a frame that updates all the IDs
        '''
        if spawnframe not in self.update_frames:
            raise KeyError('spawnframe not a spawn frame')
        
        output = {}
        for replications in self.data['content']['body']['frames'][spawnframe]['replications']:
            if 'spawned' not in replications['value'].keys():
                continue
            output[replications['actor_id']['value']] = replications['value']['spawned']['class_name']
        
        return dict(sorted(output.items()))
    
    def get_ids(self, obj='TAGame.Car_TA', spawnframe=0, frame=None):
        '''
        Takes a named object and spawnframe and returns what ID is attributed to that (or those) object(s)
        
        :param obj: str, the name of an object to search
        :param spawnframe: int, a frame that updates all the IDs
        :optional param frame: overrides spawnframe, takes any frame and will find the appropriate spawnframe
        '''
        if obj not in self.data['content']['body']['objects']:
            raise KeyError('object not found')
        
        if frame is not None:
            spawnframe = self.get_spawnframe(frame)
        helper = self.find_ids(spawnframe=spawnframe)
        return sorted([x for x in helper if helper[x] == obj])
    
    def find_teams(self, spawnframe=None, frame=None):
        '''
        Identifies which cars are on which teams for each given update frame
        Returns a dictionary where the update frames are the keys and the values are dictionaries of teams
        Optionally, it takes an argument 'spawnframe' or 'frame' to return only a single dictionary for a certain spawn frame

        :optional param spawnframe: specifies a single frame to select
        :optional param frame: overrides spawnframe, takes any frame and will find the appropriate spawnframe
        '''
        output = {}
        updates = self.update_frames
        if frame is not None:
            spawnframe = self.get_spawnframe(frame)
        if spawnframe is not None:
            if spawnframe not in self.update_frames:
                raise KeyError('spawnframe not in updates')
            updates = [spawnframe]
            
        for update in updates:
            teams = {0: [], 1: []}
            cars = self.get_ids(spawnframe=update)
            for replication in self.data['content']['body']['frames'][update]['replications']:
                if 'spawned' in replication['value'].keys():
                    continue
                if replication['actor_id']['value'] not in cars:
                    continue
                updated = replication['value']['updated']

                for entry in updated:
                    if entry['id']['value'] != PhysPar.COLOR_ID: # 66 indicates car color for some reason
                        continue
                    teams[entry['value']['team_paint']['team']].append(replication['actor_id']['value'])
            output[update] = teams
        
        if spawnframe is not None:
            return output[spawnframe]
        return output

    def get_physics(self, ball=True, cars=True, interpolate=True):
        '''
        Given the data, returns json-style format of all the physics in the game.
        Can be used to select only ball or car data
        '''
        output = {}

        if not (ball or cars):
            raise AttributeError('at least one of ball or cars must be True')
        if self.update_frames[0]:
            raise AttributeError('update_frames formatted incorrectly (first entry should be 0)')
        update_pointer = 0
        all_frames = self.data['content']['body']['frames']
        ball_id = []
        car_ids = []

        for i, frame in enumerate(all_frames):
            if update_pointer != len(self.update_frames) - 1 and i == self.update_frames[update_pointer]:
                if ball: ball_id = self.get_ids(obj='TAGame.Ball_TA', spawnframe=self.update_frames[update_pointer])
                if cars:
                    car_ids = self.get_ids(obj='TAGame.Car_TA', spawnframe=self.update_frames[update_pointer])
                    teams = self.find_teams(spawnframe=self.update_frames[update_pointer])
                update_pointer += 1
            search = ball_id.copy()
            search.extend(car_ids)
            search = tuple(search)

            for replication in frame['replications']:
                if 'spawned' in replication['value'].keys(): continue

                actor_id = replication['actor_id']['value']
                if actor_id not in search: continue

                updated = replication['value'].get('updated')
                if updated is None: continue

                phys = None
                for entry in updated:
                    if entry['id']['value'] != PhysPar.PHYS_ID: continue     # 42 is physics ID, not sure if this works in all replays
                    phys = entry['value']['rigid_body_state'].copy()
                    break
                if phys is None: continue

                if phys['angular_velocity'] is None: continue
                    # phys['angular_velocity'] = {'x': 0, 'y': 0, 'z': 0}
                if phys['linear_velocity'] is None: continue
                    # phys['linear_velocity'] = {'x': 0, 'y': 0, 'z': 0}
                # if phys['location'] is None:
                #     phys['location'] = {'x': 0, 'y': 0, 'z': 0}
                # if phys['rotation'] is None:
                #     phys['rotation']['quaternion'] = {'w': 0, 'x': 0, 'y': 0, 'z': 0}

                key = ''
                isball = actor_id in ball_id
                if isball:
                    key = 'ball'
                else:
                    key = f'{int(actor_id in teams[1])}_car_{actor_id}'

                if output.get(i) is None: output[i] = {}
                output[i][key] = {}

                phys_attrs = ('angular_velocity', 'linear_velocity', 'location', 'rotation')
                xyz = ('x', 'y', 'z')
                for attr in phys_attrs:
                    if attr != 'rotation':
                        output[i][key][attr] = {var: phys[attr][var] for var in xyz}
                    else:
                        output[i][key][attr] = {var: phys[attr]['quaternion'][var] for var in xyz}
                        output[i][key][attr]['w'] = phys[attr]['quaternion']['w']

                ### Interpolation
                if not interpolate: continue
                if i == 0 or bool(output.get(i-1,{}).get(key,{})): continue
                num_missing = 1
                while num_missing < 5:
                    if not bool(output.get(i-num_missing,{}).get(key,{})):
                        num_missing += 1
                        continue
                    num_missing -= 1
                    for n in range(num_missing):
                        interp = i-1-n
                        if output.get(interp) is None: output[interp] = {}
                        output[interp][key] = {}

                        output[interp][key] = output[i][key]
                    break

        return output
            
    def find_goals(self):
        '''
        Given the replay, it finds the frames where the ball gets scored.
        Returns a dictionary where the key is the goal frame and the value is the scoring team
        Dedicated to Mistle Tomas
        '''
        ball_only = {frame: self.physics[frame].get('ball') for frame in self.physics if self.physics[frame].get('ball') is not None}
        scores = [mark for mark in self.data['content']['body']['marks'] if 'Goal' in mark['value']]
        possible_goals = [frame for frame in ball_only if abs(ball_only[frame]['location']['y']) > PhysPar.GOAL_Y]
        
        goal_frames = {}
        for score in scores:
            frame = score['frame']
            for goal in possible_goals:
                if goal >= frame:
                    goal_frames[goal] = int(score['value'] == 'Team1Goal')
                    break

        return goal_frames
    
    def find_kickoffs(self):
        '''
        Given the replay, this finds the frames where kickoffs start following a goal
        Returns a dictionary with the scored on frame as key and the kickoff frame as value
        Can't find kickoffs that don't follow goals
        '''
        goal_frames = list(self.find_goals().keys())[:-1]
        goal_frames.append(0)
        output = {}

        for goal_frame in goal_frames:
            window = goal_frame
            found = False
            cars_reset = False

            while not found:
                if not cars_reset:
                    cars_reset = not any([self.physics.get(i) for i in range(window, window+10)])
                if cars_reset and all([self.physics.get(window+i) for i in range(10)]):
                    output[goal_frame] = window
                    found = True
                window += 1
        return output
    
    def poss_intervals(self, threshold=0.95):
        '''
        Returns intervals of attacking possession prior to a goal. For use in making the dataset.
        Attacking possession is defined as a period where one the following are true in over 95% (or the threshold) of frames prior to the goal:
            1) The ball is moving towards the defender's net
            2) The ball is in the attacking third
        Threshold argument tunes how close to the goal your intervals will be.

        :optional param threshold: a float between 0 and 1. If 0, returns the entire range between the last kickoff and the goal
        '''
        def find_window_size(arr, threshold=0.95):
            if threshold < 0 or threshold > 1:
                raise ValueError('threshold out of bounds')
            cumsum = np.cumsum(arr)
            percentage = cumsum / np.arange(1, len(arr) + 1)
            # Find the last index where the percentage exceeds the threshold
            last_k_index = np.argmin(percentage > threshold)
            if all(percentage > threshold):
                last_k_index = len(percentage) - 1
            return last_k_index
        
        output = []
        attack_line = 170000
        goals = self.find_goals()

        for goal in goals:
            last_kickoff = max([frame for frame in set(range(max(self.physics))) - set(self.physics.keys()) if frame < goal])

            y_location = []
            y_velocity = []
            for frame in range(goal, last_kickoff, -1):
                if self.physics[frame].get('ball') is None: continue # Ball will never be None in my intervals, Ball will always be present

                y_location.append(self.physics[frame]['ball']['location']['y'])
                y_velocity.append(self.physics[frame]['ball']['linear_velocity']['y'])

            y_location = np.array(y_location)
            y_velocity = np.array(y_velocity)

            # Invert all values if team 1 scores bc they're attacking on the negative side
            if goals[goal]:
                y_location *= -1
                y_velocity *= -1
            
            loc_cond = y_location > attack_line
            vel_cond = y_velocity > 0

            together = np.logical_or(loc_cond, vel_cond)

            output.append((goal - find_window_size(together, threshold), goal))
        
        return output
    
    def time_before_goals(self):
        '''
        Function returns a list of how many seconds the attacking possesion started before each goal
        '''
        intervals = self.poss_intervals()
        return [(interval[1] - interval[0]) / 30 for interval in intervals]
    
    def create_feature(self, frame, scorer=None, verbose=False):
        '''
        Function takes a frame and returns a feature vector attributed to it.
        Optionally, you can include who scores which will include the scorer as the first element

        :param frame: int of frame
        :optional param scorer: Int of who scores the next goal
        '''
        # Helper function
        def get_leaf_nodes(dictionary, val_only=False):
            leaf_nodes = []

            def _get_leaf_nodes_recursive(sub_dict, path=[]):
                for key, value in sub_dict.items():
                    current_path = path + [key]
                    if isinstance(value, dict):
                        _get_leaf_nodes_recursive(value, current_path)
                    else:
                        leaf_nodes.append({'path': current_path, 'value': value})

            _get_leaf_nodes_recursive(dictionary)

            if not val_only:
                return leaf_nodes

            return [node['value'] for node in leaf_nodes]

        frame_feature = []

        if scorer is not None:
            if scorer not in (0, 1):
                raise ValueError('scorer not a team, should be 0 or 1')
            frame_feature = [scorer]

        phys_snapshot = self.physics[frame]

        objects = phys_snapshot.keys()

        if 'ball' not in objects:
            if verbose: print(f'Ball not in frame {frame}')
            return None # This should never happen, but just in case
        
        ball = ['ball']
        team0 = set([car for car in objects if car[0] == '0'])
        team1 = set([car for car in objects if car[0] == '1'])
        objects = (ball, team0, team1)

        for sublist in objects:
            if len(sublist) > PhysPar.TEAM_SIZE:
                return self.create_feature(frame=frame+1, scorer=scorer)

            for item in sublist:
                frame_feature += get_leaf_nodes(phys_snapshot[item], val_only=True)

            if 'ball' in sublist: continue
            if len(sublist) == PhysPar.TEAM_SIZE: continue

            num_missing = PhysPar.TEAM_SIZE - len(sublist)
            
            frame_feature += [0] * 13 * num_missing

        if len(frame_feature) != 91 and len(frame_feature) != 92:
            print(f'Feature not proper length on frame {frame}')
            return None
        
        return frame_feature
    
    def shave_phys(self, slice_interval=15, threshold=0.95):
        '''
        Function returns a shaved version of the dataset with labels as the first element and physics in the later elements.
        Schema is as follows [scorer, ball: {av: {x,y,z}, lv: {x,y,z}, loc: {x,y,z}, rot: {x,y,z,w}}, 0car1, 0car2, 0car3, 1car#]
        The cars have the same physics features as the ball, and team 1 has the same number of cars as 0
        If a car is demoed and not present, all of its features are 0 which may cause an issue because a car could in theory actually have those values

        :optional param slice_interval: How many frames this function waits before grabbing another feature
        '''
        intervals = self.poss_intervals(threshold=threshold)
        goals = self.find_goals()
        dataset = []

        for interval in intervals:
            scorer = goals[interval[1]]
            for i in range(*interval, slice_interval):
                frame_feature = self.create_feature(i, scorer)
                if frame_feature is None: continue

                dataset.append(frame_feature)
        
        return dataset