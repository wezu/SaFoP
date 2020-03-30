'''Standalone Fonline Planer (SaFoP)
LICENSE:
    Copyright (c) 2020, wezu (wezu.dev@gmail.com)
    Permission to use, copy, modify, and/or distribute this software for any
    purpose with or without fee is hereby granted, provided that the above
    copyright notice and this permission notice appear in all copies.
    THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
    WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
    MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
    ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
    WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN
    AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING
    OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
INFO:
    To run this program you will need to install Python and Kivy.
'''
from kivy.config import Config
Config.set('graphics', 'position', 'custom')
Config.set('graphics', 'left', 0)
Config.set('graphics', 'top',  60)
Config.set('graphics', 'width', '700')
Config.set('graphics', 'height', '400')
Config.set('input', 'mouse', 'mouse,disable_multitouch')
Config.set('kivy', 'exit_on_escape', '0')
Config.set('kivy','window_icon','data/icon-32.png')

from kivy.clock import Clock
from kivy.app import App
from kivy.uix.modalview import ModalView
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.gridlayout import GridLayout
from kivy.uix.textinput import TextInput

from kivy.lang import Builder

from copy import deepcopy
from collections import defaultdict
import json
import os
import random

#classes used by the pop-ups
#added here so they can be styled within the .kv and used from python
class CustomPopup(ModalView):
    pass

class PopupLabel(Label):
    pass

class PopupGridLayout(GridLayout):
    pass

class PopupButton(Button):
    pass

class PopupInput(TextInput):
    pass

class dotdict(defaultdict):
    '''Dictionary with attribute access to keys (using '.').
    It also has a default value for missing keys (0),
    a custom str format and can be deep-copied.
    '''
    def __init__(self, input_dict=None):
        if input_dict:
            super().__init__(int, input_dict)
        else:
            super().__init__(int)

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            # is this needed..?
            # defaultdict should return a default value
            if key.startswith('__'):
                raise AttributeError(key)
            else:
                self[key] = 0
                return 0

    def __setattr__(self, key, value):
        self[key] = value

    def __str__(self):
        s='\n'
        for key, value in self.items():
            s+=key+': '
            s+=str(value)+'\n'
        return s

    def __deepcopy__(self, memo=None):
        dict_copy = dotdict()
        for key, value in self.items():
            dict_copy[key]=deepcopy(value)
        return dict_copy

#some const for readability.
PERK_TYPE_SUPPORT = 1
PERK_TYPE_NORMAL = 2
PERK_TYPE_CLASS = 3

#setup containers for the stats
#most don't need to be set, but they are here for reference
pc = dotdict()
pc.level = 1
#special
pc.min_special = 1
pc.max_special = 10
pc.special = dotdict()
pc.special.S = 5
pc.special.P = 5
pc.special.E = 5
pc.special.C = 5
pc.special.I = 5
pc.special.A = 5
pc.special.L = 5
pc.special_points = 5
#perks
pc.perk_every_levels = 3
pc.perk_points = 0
pc.perks = dotdict()
pc.class_perk = None
#trait
pc.traits = []
#criticals
pc.head_critical_resist_tier = 0
pc.critical_resist_tier = 0
pc.critical_resist = 0
pc.critical_power_tier = 0
pc.critical_power=0
pc.critical_chance=0
pc.hth_critical_power=0
pc.hth_critical_chance=0
#base hit points
pc.hit_points = 0
#extra dmg
pc.per_bullet_dmg=0
pc.bonus_damage=0
pc.flat_damage=0
pc.flat_fire_damage=0
pc.melee_damage=0
#dr/dt
pc.dr=dotdict()
pc.dr.normal = 0
pc.dr.laser = 0
pc.dr.plasma = 0
pc.dr.fire = 0
pc.dr.explode = 0
pc.dr.electric = 0
pc.dt=dotdict()
pc.dt.normal = 0
pc.dt.laser = 0
pc.dt.plasma = 0
pc.dt.fire = 0
pc.dt.explode = 0
pc.dt.electric = 0
#skills
pc.skill = dotdict()
pc.skill_points = 0
pc.read_books = dotdict()
pc.read_books_points = dotdict()
pc.bonus_skill_points = 0
#drugs
pc.drugs = []
pc.max_drugs = 5
pc.drug_duration =30
#temp bonus - probably only drugs changing special
pc.bonus = dotdict()
pc.bonus.special = dotdict()
#implants
pc.implants = dotdict()
pc.implants_special = dotdict()
pc.max_implants = 5
pc.max_implant_level = 2
pc.max_implants_special = 6
#other?
pc.healing_rate = 0
pc.bonus_hit_points = 0
pc.xp_bonus = 0
pc.speed = 100
pc.party_points=0
pc.rad_resist=0
pc.poision_resist=0
pc.carry_weight =0
pc.action_points=0
pc.armor_class =0
pc.sequence=0
pc.tb_move_ap=0
pc.fov_bonus=0

#Helper functions:

def idf(name):
    '''Turn name into a id-string'''
    return name.replace(' ', '_').lower()

def anti_cmd(cmd, temp_char='$'):
    '''Replace + with - and - with +
    temp_char should be a character not present in the input string'''
    return cmd.replace('+',temp_char).replace('-', '+').replace(temp_char,'-')

def skill_cost(value):
    '''Return the skill point cost of a skill based on the skill value'''
    if value <= 150:
        return 1
    elif value <= 175:
        return 2
    elif value <= 200:
        return 3
    elif value <= 225:
        return 4
    elif value <= 250:
        return 5
    else:
        return 6

class PlanerApp(App):
    def __init__(self, *kwargs):
        super().__init__(*kwargs)
        self.title = 'SaFoP by wezu'
        self._skill_interval = None
        self._last_skill = None
        self._last_amount = 0
        self.known_traits ={}
        self.level_history =[]
        self.min_skill_level={}
        #in refresh mode only the ui should be updated
        self.refresh_mode = False
        #load traits data
        with open('data/traits.txt') as infile:
            for line in infile.readlines():
                if not line.startswith('#'):
                    #turn long str to list
                    line_as_list = [i.strip() for i in line.split(';')]
                    name = line_as_list[0]
                    id = idf(name)
                    effect = [i.strip() for i in line_as_list[1].split(',')]
                    self.known_traits[id]={'name':name, 'effect':effect}
        #load skill data
        self.known_skills={}
        with open('data/skills.txt') as infile:
            for line in infile.readlines():
                if not line.startswith('#'):
                    #turn long str to list
                    line_as_list = [i.strip() for i in line.split(';')]
                    name = line_as_list[0]
                    id = idf(name)
                    limit = int(line_as_list[1])
                    start_value = line_as_list[2]
                    self.known_skills[id]={'name':name, 'limit':limit, 'start_value':start_value}
        #load perks data
        self.known_perks={}
        self.known_perks_support ={}
        self.known_perks_class ={}
        with open('data/perks.txt') as infile:
            for line in infile.readlines():
                if not line.startswith('#'):
                    line_as_list = [i.strip() for i in line.split(';')]
                    id = line_as_list[0].replace(' ', '_').lower()
                    name = line_as_list[0]
                    effect =[i.strip() for i in line_as_list[1].split(',')]
                    level = int(line_as_list[2])
                    type = int(line_as_list[3])
                    req = line_as_list[4]
                    desc = line_as_list[5]
                    if type == PERK_TYPE_SUPPORT:
                        self.known_perks_support[id]={'name':name, 'level':level,
                                                        'req':req, 'desc':desc, 'effect':effect}
                    elif type == PERK_TYPE_NORMAL:
                        self.known_perks[id]={'name':name, 'level':level, 'req':req,
                                                'desc':desc, 'effect':effect}
                    elif type == PERK_TYPE_CLASS:
                        self.known_perks_class[id]={'name':name, 'level':level, 'req':req,
                                                      'desc':desc, 'effect':effect}
        #load drugs data
        self.known_drugs={}
        with open('data/drugs.txt') as infile:
            for line in infile.readlines():
                if not line.startswith('#'):
                    #turn long str to list
                    line_as_list = [i.strip() for i in line.split(';')]
                    name = line_as_list[0]
                    id = idf(name)
                    effect = [i.strip() for i in line_as_list[1].split(',')]
                    self.known_drugs[id]={'name':name, 'effect':effect}
        #load implants data
        self.known_implants={}
        with open('data/implants.txt') as infile:
            for line in infile.readlines():
                if not line.startswith('#'):
                    #turn long str to list
                    line_as_list = [i.strip() for i in line.split(';')]
                    name = line_as_list[0]
                    id = idf(name)
                    effect_1 = [i.strip() for i in line_as_list[1].split(',')]
                    effect_2 = [i.strip() for i in line_as_list[2].split(',')]
                    effect_3 = [i.strip() for i in line_as_list[3].split(',')]
                    self.known_implants[id]={'name':name, 'effect_1':effect_1, 'effect_2':effect_2, 'effect_3':effect_3}

    def _install_settings_keys(self, window):
        '''Added to disable Kivy F1 settings '''
        pass

    def save_load_popup(self):
        '''Show save/load popup'''
        self.popup = CustomPopup()
        scroll = ScrollView()

        grid = PopupGridLayout()
        save_header = PopupLabel(text='SAVE CHARACTER AS:')
        grid.add_widget(save_header)

        self.save_input = PopupInput(text='test_char.json')
        grid.add_widget(self.save_input)

        save_button = PopupButton(text='Click here to save!', on_release=self.write_save)
        grid.add_widget(save_button)

        load_header = PopupLabel(text='\nLOAD CHARACTER:')
        grid.add_widget(load_header)

        for savefile in os.listdir('save'):
            b = PopupButton(text=savefile, on_release=self.load_from_file)
            grid.add_widget(b)

        scroll.add_widget(grid)
        self.popup.add_widget(scroll)
        self.popup.open()

    def load_from_file(self, button):
        '''Load a char from file'''
        filename=button.text
        feedback =''
        level_data = None
        try:
            with open('save/'+filename) as f:
                level_data = json.load(f, object_pairs_hook=dotdict)
        except BaseException as error:
            feedback = 'Error:\n {}'.format(error)
        if not level_data:
            feedback += '\nError:\nLoaded file is empty!'
        else:
            self.level_history = level_data
        #close save popup
        self.popup.dismiss()
        if feedback:
            #open feedback popup
            self.popup = CustomPopup(size_hint=( .7, .6))
            feedback+='\nThe Program may now be unstable, please restart.\n'
            feedback+='\n\n(Click outside this popup to close it)'
            label = PopupLabel(text=feedback)
            self.popup.add_widget(label)
            self.popup.open()
        else:
            self.level_restore()

    def write_save(self, button=None):
        '''Write a save file '''
        feedback =''
        name = self.save_input.text
        #sanitize name
        name= ''.join( x for x in name if (x.isalnum() or x in "._- "))
        if not name.endswith('.json'):
            name+='.json'
        #check if file exists, no override
        if os.path.exists('save/'+name):
            feedback+='Error:\nThe file '+name+' already exists.'
        else:
            full_char = deepcopy(self.level_history)
            full_char.append(pc)
            try:
                with open('save/'+name, 'w') as json_file:
                    json.dump(full_char, json_file, indent = 4)
                feedback = 'File saved as:\n'+name
            except BaseException as error:
                feedback = 'Error:\n {}'.format(error)
        #close save popup
        self.popup.dismiss()
        #open feedback popup
        self.popup = CustomPopup(size_hint=( .7, .6))
        feedback+='\n\n(Click outside this popup to close it)'
        label = PopupLabel(text=feedback)
        self.popup.add_widget(label)
        self.popup.open()

    def _update_start_skills(self):
        '''Set the starting skills based on SPECIAL and traits
        the values are taken from skill.txt,
        Bloody Mess is the only hardcoded exception.
        This function is called when SPECIAL and Traits change.'''
        if self.refresh_mode:
            return
        for id, skill in self.known_skills.items():
            pc.skill[id]=eval(skill['start_value'])
            if 'bloody_mess' in pc.traits:
                pc.skill[id] -= 20
            #print(pc.skill[id])
            self.root.ids[id].text = str(pc.skill[id])

    def _update_special(self):
        '''Update the SPECIAL labels, check if the char is ready to level up.
        Called when SPECIAL change.
        '''
        if self.refresh_mode:
            return
        all_special_ok = True
        for spec in 'SPECIAL':
            self.root.ids['special_'+spec.lower()].text = str(pc.special[spec])
            self.root.ids['points_left'].text = str(pc.special_points)
            if pc.special[spec] < pc.min_special or pc.special[spec] > pc.max_special:
                all_special_ok = False
        if pc.level>1:
            return
        #ready to level up?
        if pc.special_points == 0 and all_special_ok:
            self.root.ids.level_up.disabled = False
            self.root.ids.level_up_all.disabled = False
        else:
            self.root.ids.level_up.disabled = True
            self.root.ids.level_up_all.disabled = True
        #update starting values for skills and hp
        self._update_start_skills()
        pc.hit_points = 65 + pc.special.S + pc.special.E

    def _update_perks(self):
        '''Check if the character meets requirements for perks.
        Called on level up and skill change.
        '''
        #check for support perks compliance
        for perk_id, perk in self.known_perks_support.items():
            if perk['level']<=pc.level and self.root.ids['perk_'+perk_id].state=='normal':
                if eval(perk['req']):
                    self.root.ids['perk_'+perk_id].disabled = False
        #check for perks compliance
        if pc.perk_points > 0:
            for perk_id, perk in self.known_perks.items():
                if perk['level']<=pc.level and self.root.ids['perk_'+perk_id].state=='normal':
                    if eval(perk['req']):
                        self.root.ids['perk_'+perk_id].disabled = False
        #check for class perks
        if not pc.class_perk:
            for perk_id, perk in self.known_perks_class.items():
                if perk['level']<=pc.level and self.root.ids['perk_'+perk_id].state=='normal':
                    self.root.ids['perk_'+perk_id].disabled = False

    def get_carry_weight(self):
        '''Returns the max carry weight '''
        #based on aftertimes parameters.fos
        #small_frame = 1 if 'small_frame' in pc.traits else 0
        #cw = 25 + pc.special.S * (25 - small_frame*10))+20000
        #cw /=2.20462262184878 #no idea what accuracy is used in fo

        #based on wiki, should be the same??
        cw = 20 + pc.carry_weight
        if 'small_frame' in pc.traits:
            cw +=  (25+pc.special.S*15)/2.2 # /2.2 is conversion from lbs to grams
        else:
            cw +=  (25+pc.special.S*25)/2.2
        if 'pack_rat' in pc.perks:
            cw*=1.33
        if pc.class_perk == 'priest':
            cw*=0.5
        return round(cw, 2)

    def get_healing_rate(self):
        hr=max(3, (pc.special.E+pc.bonus.special.E)//2)+pc.healing_rate
        if pc.class_perk == 'priest':
            hr*=2
        if pc.class_perk == 'chosen_one':
            hr = hr//2
        return hr

    def update_stats(self, widget=None):
        '''Update the stats summary,
        Called when the stats tab is opened (un-collapsed)
        '''
        if widget:
            if widget.collapse:
                return
        text='Level: '+str(pc.level)+'\n'
        text+='Attributes:\n'
        for spec in 'SPECIAL':
            value=min(20, max(1, pc.special[spec]+pc.bonus.special[spec]))
            text+=' '+spec+': '+str(value)+'\n'
        text+='\nTraits:\n'
        if not pc.traits:
            text+=' None\n'
        for trait in pc.traits:
            text+= '-'+self.known_traits[trait]['name']+'\n'
        text+='\nPerks:\n'
        for perk, level in pc.perks.items():
            if perk in self.known_perks:
                text+=' '+str(level)+'. '+self.known_perks[perk]['name']+'\n'
        text+='\nSupport Perks:\n'
        for perk, level in pc.perks.items():
            if perk in self.known_perks_support:
                text+=' '+str(level)+'. '+self.known_perks_support[perk]['name']+'\n'
        text+='\nClass Perks:\n'
        if not pc.class_perk:
            text+=' None\n'
        else:
            text+=' '+self.known_perks_class[pc.class_perk]['name']+'\n'
        text+='\nHit Points:\n '+str(pc.hit_points+pc.bonus_hit_points)+'\n'
        text+='\nAction Points:\n '+str(5+(pc.special.A+pc.bonus.special.A)//2+pc.action_points)+'\n'
        sight_range = 20+(pc.special.P+pc.bonus.special.P)*3 + pc.view_range
        text+='\nView Range:\n'
        text+=' -Front:        '+str(sight_range)+'\n'
        text+=' -Forward-side: '+str(sight_range-3)+'\n'
        text+=' -Back-side:    '+str(sight_range-11)+'\n'
        text+=' -Back:         '+str(sight_range-14)+'\n'
        text+='\nDetect sneak (300) at range:\n'
        text+=' -Front:        '+str(max(3, sight_range-(300-72)//6))+'\n'
        text+=' -Forward-side: '+str(max(3, sight_range-(300-36)//6))+'\n'
        text+=' -Back-side:    '+str(max(3, sight_range-(300-12)//6))+'\n'
        text+=' -Back:         '+str(max(3, sight_range-(300)//6))+'\n'

        text+='\nDetected when sneaking (front):\n'
        text+='-vs 1 PE:    '+ str( max(3, (20+1*3)-((pc.skill.sneak-72)//6)) )+'\n'
        text+='-vs 5 PE:    '+ str( max(3, (20+5*3)-((pc.skill.sneak-72)//6)) )+'\n'
        text+='-vs 10 PE:   '+ str( max(3, (20+10*3)-((pc.skill.sneak-72)//6)) )+'\n'
        text+='-vs 15 PE:   '+ str( max(3, (20+15*3)-((pc.skill.sneak-72)//6)) )+'\n'
        text+='-vs 20 PE:   '+ str( max(3, (20+20*3)-((pc.skill.sneak-72)//6)) )+'\n'


        text+='\nCritical Chance: (ranged/melee)\n'
        base_cc = (pc.special.L+pc.bonus.special.L)+pc.critical_chance
        base_cc_melee = (pc.special.L+pc.bonus.special.L)+pc.hth_critical_chance
        text+=' -Unaimed:    '+str(base_cc)+'% / '+str(base_cc_melee)+'%\n'
        aim_bonus = 60 * (60 + 4 * pc.special.L) // 100
        text+=' -Eye:        '+str(base_cc+aim_bonus)+'% / '+str(base_cc_melee+aim_bonus)+'%\n'
        aim_bonus = 40 * (60 + 4 * pc.special.L) // 100
        text+=' -Head:       '+str(base_cc+aim_bonus)+'% / '+str(base_cc_melee+aim_bonus)+'%\n'
        aim_bonus = 30 * (60 + 4 * pc.special.L) // 100
        text+=' -Groin:      '+str(base_cc+aim_bonus)+'% / '+str(base_cc_melee+aim_bonus)+'%\n'
        aim_bonus = 30 * (60 + 4 * pc.special.L) // 100
        text+=' -Arms:       '+str(base_cc+aim_bonus)+'% / '+str(base_cc_melee+aim_bonus)+'%\n'
        aim_bonus = 20 * (60 + 4 * pc.special.L) // 100
        text+=' -Legs:       '+str(base_cc+aim_bonus)+'% / '+str(base_cc_melee+aim_bonus)+'%\n'

        text+='\nCritical Power:\n '
        text+=str((pc.special.L+pc.bonus.special.L)+pc.critical_power)

        text+=' (melee: '+str((pc.special.L+pc.bonus.special.L)+pc.hth_critical_power)+')\n'
        text+='\nCarry Weight:\n '+str(self.get_carry_weight())+'kg\n'
        text+='\nSequence:\n '+str((pc.special.P+pc.bonus.special.P)*2+pc.sequence)+'\n'
        melee_dmg = max(1, (pc.special.S+pc.bonus.special.S-5) * (1 if 'bruiser' in pc.traits else 2))
        text+='\nMelee Damage:\n '+str(melee_dmg+pc.melee_damage)+'\n'
        text+='\nHealing Rate:\n '+str(self.get_healing_rate())+'\n'
        text+='\nArmor Class:\n  '+str((pc.special.A+pc.bonus.special.A)*3+pc.armor_class)+'\n'
        text+='\nPoison Resistance:\n '+str((pc.special.E+pc.bonus.special.E)*5+pc.poision_resist)+'\n'
        text+='\nRadiation Resistance:\n '+str((pc.special.E+pc.bonus.special.E)*2+pc.rad_resist)+'\n'
        text+='\nRun Speed:\n '+str(pc.speed)+'%\n'
        text+='\nDamage Resistance/Damage Threshold:\n'
        text+=' Normal:   '+str(min(90, pc.dr.normal))+'/'+str(pc.dt.normal)+'\n'
        text+=' Laser:    '+str(min(90, pc.dr.laser))+'/'+str(pc.dt.laser)+'\n'
        text+=' Fire:     '+str(min(90, pc.dr.fire))+'/'+str(pc.dt.fire)+'\n'
        text+=' Plasma:   '+str(min(90, pc.dr.plasma))+'/'+str(pc.dt.plasma)+'\n'
        text+=' Explode:  '+str(min(90, pc.dr.explode))+'/'+str(pc.dt.explode)+'\n'
        text+=' Electric: '+str(min(90, pc.dr.electric))+'/'+str(pc.dt.electric)+'\n'

        text+='\nSkill Points per Level:\n '
        skill_points = pc.bonus_skill_points
        if 'gifted' in pc.traits:
            skill_points += pc.special.I
        else:
            skill_points += 5+pc.special.I*3
        text+=str(skill_points)+'\n'

        text+='\nSkills:\n'
        for skill_id, skill in self.known_skills.items():
            #text+=' -'+skill['name']+': '+str(pc.skill[skill_id])+'\n'
            text+=' -{name:16}{value}\n'.format(name=skill['name'], value=pc.skill[skill_id])
        self.root.ids.stats_txt.text = text

    def add_randomboy(self, button=None):
        '''Add the randomboy bonuses to the character '''
        for key, value in self.last_randomboy.items():
            if key in pc.special:
                pc.special[key]+=value
            if key=='Hit Points':
                pc.bonus_hit_points+=value
            if key=='Action Points':
                pc.action_points+=value
            if key=='Armor Class':
                pc.armor_class+=value
            if key=='Melee Damage':
                pc.melee_damage+=value
            if key=='Carry Weight':
                pc.carry_weight+=value
            if key=='Sequence':
                pc.sequence+=value
            if key=='Healing Rate':
                pc.healing_rate+=value
            if key=='Critical Chance':
                pc.critical_chance+=value
            if key=='TB Move AP':
                pc.tb_move_ap+=value

            if key=='Normal DT':
                pc.dt.normal+=value
            if key=='Laser DT':
                pc.dt.laser+=value
            if key=='Plasma DT':
                pc.dt.plasma+=value
            if key=='Fire DT':
                pc.dt.fire+=value
            if key=='Explode DT':
                pc.dt.explode+=value
            if key=='Electric DT':
                pc.dt.electric+=value

            if key=='Normal DR':
                pc.dr.normal+=value
            if key=='Laser DR':
                pc.dr.laser+=value
            if key=='Plasma DR':
                pc.dr.plasma+=value
            if key=='Fire DR':
                pc.dr.fire+=value
            if key=='Explode DR':
                pc.dr.explode+=value
            if key=='Electric DR':
                pc.dr.electric+=value
        self.popup.dismiss()

    def randomize_randomboy(self, button=None):
        '''Reroll the bonus stats'''
        self.last_randomboy= self.roll_random_boy()
        bonus_text='BONUS STATS:\n'
        for key, value in self.last_randomboy.items():
            bonus_text+=key+': '+str(value)+'\n'
        self.rb_bonus_tabel.text=bonus_text

    def roll_random_boy(self):
        '''Roll randomboy bonus'''
        bonus={}
        if random.random()<=0.75:
            bonus['S']=random.randint(-4,3)
        if random.random()<=.75:
            bonus['P']=random.randint(-4,3)
        if random.random()<=0.75:
            bonus['E']=random.randint(-4,3)
        if random.random()<=0.75:
            bonus['C']=random.randint(-4,3)
        if random.random()<=0.75:
            bonus['I']=random.randint(-4,3)
        if random.random()<=0.75:
            bonus['A']=random.randint(-4,3)
        if random.random()<=0.75:
            bonus['L']=random.randint(-4,3)
        if random.random()<=0.95:
            bonus['Hit Points']=random.randint(-100, 80)
        if random.random()<=0.15:
            bonus['Action Points']=random.randint(-3, 2)
        if random.random()<=0.65:
            bonus['Armor Class']=random.randint(-40, 50)
        if random.random()<=0.40:
            bonus['Melee Damage']=random.randint(-10, 8)
        if random.random()<=0.95:
            bonus['Carry Weight']=random.randint(-50, 40)
        if random.random()<=0.5:
            bonus['Sequence']=random.randint(-10, 8)
        if random.random()<=0.3:
            bonus['Healing Rate']=random.randint(-25, 20)
        if random.random()<=0.20:
            bonus['Critical Chance']=random.randint(-10, 8)
        if random.random()<=0.75:
            bonus['TB Move AP']=random.randint(0, 7)

        if random.random()<=0.25:
            bonus['Normal DT']=random.randint(-4, 3)
        if random.random()<=0.25:
            bonus['Laser DT']=random.randint(-4, 3)
        if random.random()<=0.25:
            bonus['Plasma DT']=random.randint(-4, 3)
        if random.random()<=0.25:
            bonus['Fire DT']=random.randint(-4, 3)
        if random.random()<=0.25:
            bonus['Explode DT']=random.randint(-4, 3)
        if random.random()<=0.25:
            bonus['Electric DT']=random.randint(-4, 3)

        if random.random()<=0.4:
            bonus['Normal DR']=random.randint(-10, 7)
        if random.random()<=0.4:
            bonus['Laser DR']=random.randint(-10, 7)
        if random.random()<=0.4:
            bonus['Plasma DR']=random.randint(-10, 7)
        if random.random()<=0.4:
            bonus['Fire DR']=random.randint(-10, 7)
        if random.random()<=0.4:
            bonus['Explode DR']=random.randint(-10, 7)
        if random.random()<=0.4:
            bonus['Electric DR']=random.randint(-10, 7)
        return bonus

    def perk_effect(self, perk):
        '''Hardcoded effects of perks that are too complex'''
        if perk == 'deathclaw':
            pc.special.S+=3
            pc.dr.normal+=40+pc.special.L+pc.bonus.special.L+pc.critical_chance
            pc.dr.laser+=40+pc.special.P+pc.bonus.special.P
            pc.dr.fire+=40+self.get_healing_rate()
            pc.dr.plasma+=40+pc.special.I+pc.bonus.special.I
            pc.dr.explode+=40+pc.special.E+pc.bonus.special.E
            pc.dr.electric+=40+(5+(pc.special.A+pc.bonus.special.A)//2+pc.action_points)

            pc.dt.normal+=6+pc.special.I+pc.bonus.special.I
            pc.dt.laser+=7+pc.special.C+pc.bonus.special.C
            pc.dt.fire+=4+(pc.special.P+pc.bonus.special.P)*2+pc.sequence
            pc.dt.plasma+=5+pc.special.L+pc.bonus.special.L
            pc.dt.explode+=6+pc.special.A+pc.bonus.special.A
            pc.dt.electric+=3+pc.special.P+pc.bonus.special.P

            #2x melee dmg - but calculated with current stats
            #we just calc melee damage and add it as melee damage
            base_melee_dmg= max(1, (pc.special.S+pc.bonus.special.S-5) * (1 if 'bruiser' in pc.traits else 2))
            pc.melee_damage+=pc.melee_damage+base_melee_dmg
            #speed bonus
            pc.speed+=10
        elif perk == 'soldier':
            pc.special.S+=1
            pc.special.P+=1
            pc.special.E+=1
            pc.special.C+=1
            pc.special.I+=1
            pc.special.A+=1
            pc.special.L+=1
            pc.action_points+=1
            pc.armor_class+=1
            pc.melee_damage+=1
            pc.carry_weight+=1
            pc.sequence+=1
            pc.healing_rate+=1
            pc.critical_chance+=1
            pc.rad_resist+=1
            pc.poision_resist+=1
            pc.tb_move_ap+=1
            for skill_id, skill in self.known_skills.items():
                pc.skill[skill_id]+=1
            pc.per_bullet_dmg+=1
            pc.max_implants +=1
            pc.max_implants_special += 1
            pc.flat_damage+=1
            pc.critical_power_tier += 1
            pc.critical_power+=1
            for dt in pc.dt.values():
                dt+=1
            for dr in pc.dr.values():
                dr+=1
            #more???
        elif perk =='random_boy':
            self.last_randomboy=self.roll_random_boy()

            self.popup = CustomPopup(auto_dismiss=False)
            scroll = ScrollView()
            grid = PopupGridLayout()

            save_button = PopupButton(text='USE THESE STATS', on_release=self.add_randomboy)
            grid.add_widget(save_button)
            reroll_button = PopupButton(text='RANDOMIZE!', on_release=self.randomize_randomboy)
            grid.add_widget(reroll_button)

            bonus_text='BONUS STATS:\n'
            for key, value in self.last_randomboy.items():
                bonus_text+=key+': '+str(value)+'\n'

            self.rb_bonus_tabel = PopupLabel(text=bonus_text)
            grid.add_widget(self.rb_bonus_tabel)

            scroll.add_widget(grid)
            self.popup.add_widget(scroll)
            self.popup.open()
        elif perk == 'mutant':
            pc.special.E+=3
            pc.hit_points+=pc.hit_points+pc.bonus_hit_points+100

    def add_perk(self, button):
        '''Adds or removes a perk.
        The perk and state are taken from the button attributes.
        Called when clicked on a perk button
        '''
        if self.refresh_mode:
            return
        name = button.text
        id = idf(name)
        if button.state == 'down':# add perk
            pc.perks[id] = int(pc.level)
            #check if it's support perk, normal perk or class perk
            if id in self.known_perks:
                perk_dict = self.known_perks
                pc.perk_points -= 1
                for perk_id in self.known_perks:
                    if perk_id != id and self.root.ids['perk_'+perk_id].state == 'normal':
                        self.root.ids['perk_'+perk_id].disabled = True
            elif id in self.known_perks_class:
                perk_dict = self.known_perks_class
                pc.class_perk = id
                for perk_id in self.known_perks_class:
                    self.root.ids['perk_'+perk_id].disabled = True
            elif id in self.known_perks_support:
                perk_dict = self.known_perks_support
            #apply effect
            for cmd in perk_dict[id]['effect']:
                exec(cmd)
        elif button.state == 'normal':#remove perk
            del pc.perks[id]
            if id in self.known_perks:
                perk_dict = self.known_perks
                pc.perk_points += 1
            elif id in self.known_perks_support:
                perk_dict = self.known_perks_support
            #class perks are complex, don't remove
            #elif id in self.known_perks_class:
            #    perk_dict = self.known_perks_class
            #    pc.class_perk = None

            #remove effect
            for cmd in perk_dict[id]['effect']:
                exec(anti_cmd(cmd))
        #update labels
        self._update_special()
        self._update_perks()
        self.enable_implants()

    def add_trait(self, button):
        '''Adds or removes a trait.
        The trait and state are taken from the button attributes.
        Called when clicked on a trait button
        '''
        if self.refresh_mode:
            return
        name = button.text
        id = idf(name)
        if button.state == 'down': #add trait
            pc.traits.append(id)
            for cmd in self.known_traits[id]['effect']:
                exec(cmd)
            if len(pc.traits) == 2:
                for trait_id in self.known_traits:
                    if self.root.ids['trait_'+trait_id].state == 'normal':
                        self.root.ids['trait_'+trait_id].disabled = True
        else: # remove trait
            del pc.traits[pc.traits.index(id)]
            for cmd in self.known_traits[id]['effect']:
                exec(anti_cmd(cmd))
            for trait_id in self.known_traits:
                self.root.ids['trait_'+trait_id].disabled = False
        #update labels
        self._update_special()

    def add_drug(self, button):
        '''Adds or removes a drug'''
        if self.refresh_mode:
            return
        name = button.text
        id = idf(name)
        if button.state == 'down': #add drug
            pc.drugs.append(id)
            for cmd in self.known_drugs[id]['effect']:
                exec(cmd)
            if len(pc.drugs) == pc.max_drugs:
                prefix='drug_'
                if 'cannibal' in pc.traits:
                    prefix='cannibal_drug_'
                for drug_id in self.known_drugs:
                    if  prefix+drug_id in self.root.ids:
                        if self.root.ids[prefix+drug_id].state == 'normal':
                            self.root.ids[prefix+drug_id].disabled = True
        else: # remove drug
            del pc.drugs[pc.drugs.index(id)]
            for cmd in self.known_drugs[id]['effect']:
                exec(anti_cmd(cmd))
            self._toggle_cannibal_drugs()
        #update labels
        self._update_special()

    def _give_book_points(self, skill):
        '''Inner logic function for actually changing the skill values.'''
        if self.refresh_mode:
            return
        pc.read_books[skill]+=1
        pc.read_books_points[skill]+=6
        value = pc.skill[skill]
        print(value, '>')
        if self.known_skills[skill]['limit'] <= value:
            return
        #mimic books.fos
        sp=pc.read_books_points[skill]
        while(sp>0):
            if value >150 and sp>3:
                pc.skill[skill]+=1
                sp=0
            elif value >150 and sp>2:
                pc.skill[skill]+=1
                sp-=3
            elif value >100 and sp>1:
                pc.skill[skill]+=1
                sp-=2
            elif value <=100 and sp>0:
                pc.skill[skill]+=1
                sp-=1
            else:
                sp=0
        #leftover points?
        pc.read_books_points[skill]=sp
        #skill limit
        if pc.skill[skill] > self.known_skills[skill]['limit']:
            pc.skill[skill] = self.known_skills[skill]['limit']
        #new minimum for reducing skills is the current value
        self.min_skill_level[skill]=pc.skill[skill]
        #update
        print(pc.skill[skill])
        self.root.ids[skill].text = str(pc.skill[skill])
        self._update_perks()

    def add_book(self, skill, level):
        '''Read book(-s), ad points, makr books as read.'''
        if self.refresh_mode:
            return
        b = self.root.ids['book_'+str(level)+'_'+skill]
        if b.disabled:
            return
        for i in range(1, level+1):
            button = self.root.ids['book_'+str(i)+'_'+skill]
            if not button.disabled:
                self._give_book_points(skill)
                button.disabled = True
                button.state = 'down'

    def _do_skill_change(self, skill, amount):
        '''Inner function to change skill values '''
        if self.refresh_mode:
            return
        if amount > 0:
            if pc.skill_points < 1:
                return False
            value = pc.skill[skill]
            if self.known_skills[skill]['limit'] <= value:
                return False
            cost = skill_cost(value+1)
            if cost > pc.skill_points:
                return False
            pc.skill[skill]+=1
            pc.skill_points-=cost
            self.root.ids[skill].text = str(pc.skill[skill])
            self.root.ids.skill_points.text = 'Skill Points: '+str(pc.skill_points)
            return True
        else:
            value = pc.skill[skill]
            min_value = self.level_history[-1]['skill'][skill]
            if skill in self.min_skill_level:
                min_value = max(min_value, self.min_skill_level[skill])
            if value <= min_value:
                return False
            cost = skill_cost(value)
            pc.skill[skill]-=1
            pc.skill_points+=cost
            self.root.ids[skill].text = str(pc.skill[skill])
            self.root.ids.skill_points.text = 'Skill Points: '+str(pc.skill_points)
            return True

    def add_skill(self, skill, amount):
        '''Add/remove skill points '''
        if self.refresh_mode:
            return
        if self._do_skill_change(skill, amount):
            self._last_skill = skill
            self._last_amount = amount
            self._skill_interval = Clock.schedule_interval(self.skill_repeat, 0.08)

    def skill_repeat(self, dt):
        '''Wrapper function called in an interval when holding the + or - skill buttons'''
        if self.refresh_mode:
            return
        self._do_skill_change(self._last_skill, self._last_amount)

    def stop_skill_interval(self):
        '''Called when the +/- skill button is released. '''
        if self.refresh_mode:
            return
        self._update_perks()
        if self._skill_interval:
            self._skill_interval.cancel()
            self._skill_interval = None
            self._last_skill = None
            self._last_amount = 0

    def _toggle_cannibal_drugs(self):
        self.refresh_mode=True
        for widget_id, widget in self.root.ids.items():
            if widget_id.startswith('cannibal_drug_'):
                widget.disabled = 'cannibal' not in pc.traits
                widget.state = 'normal'
            elif widget_id.startswith('drug_'):
                widget.disabled = 'cannibal' in pc.traits
                widget.state = 'normal'
        self.refresh_mode=False

    def add_special_implant(self, spec, level):
        '''Add/Remove special implants '''
        if self.refresh_mode:
            return
        if level > pc.implants_special[spec]:
            pc.implants_special[spec]+=1
            pc.special[spec]+=1
            button = self.root.ids['implant_special_'+str(level)+'_'+spec]
            button.disabled = True
        else:
            pc.implants_special[spec]-=1
            pc.special[spec]-=1
            if level < 12:
                button = self.root.ids['implant_special_'+str(level+1)+'_'+spec]
                button.disabled = True
        self.enable_implants()

    def add_implant(self, impl, level):
        '''Add/Remove combat implants'''
        if self.refresh_mode:
            return
        if level > pc.implants[impl]:
            pc.implants[impl]+=1
            for cmd in self.known_implants[impl]['effect_'+str(level)]:
                exec(cmd)
        else:
            pc.implants[impl]-=1
            for cmd in self.known_implants[impl]['effect_'+str(level)]:
                exec(anti_cmd(cmd))
        self.enable_implants()


    def enable_implants(self):
        '''Enable or disable implant installation '''
        #Disable all
        for widget_id, widget in self.root.ids.items():
            if widget_id.startswith('implant_'):
                widget.disabled = True
        if pc.level<30:
            return
        #Enable new
        # special implants
        installed_implants= sum(pc.implants_special.values())
        if installed_implants < pc.max_implants_special:
            for spec in 'SPECIAL':
                if pc.special[spec]<20 :
                    num_implants = pc.implants_special[spec]
                    if num_implants < pc.max_implants_special:
                        button = self.root.ids['implant_special_'+str(num_implants+1)+'_'+spec]
                        button.disabled = False
        #combat implants
        installed_implants= sum(pc.implants.values())
        if installed_implants < pc.max_implants:
            for implant_id in self.known_implants:
                num_implants = pc.implants[implant_id]
                if num_implants < pc.max_implants:
                    if num_implants < pc.max_implant_level:
                        button = self.root.ids['implant_'+implant_id+'_'+str(num_implants+1)]
                        button.disabled = False

        #for cyborg enable uninstalling implants
        if pc.class_perk == 'cyborg':
            for spec, value in pc.implants_special.items():
                if value > 0:
                    button = self.root.ids['implant_special_'+str(value)+'_'+spec]
                    button.disabled = False
            for implant_id, value in pc.implants.items():
                if value > 0:
                    button = self.root.ids['implant_'+implant_id+'_'+str(value)]
                    button.disabled = False

    def refresh_all(self):
        '''Refresh UI without changing any inner values'''
        self.refresh_mode = True
        #update level label
        self.root.ids.level_label.text = 'Level: '+str(pc.level)
        #special
        for spec in 'SPECIAL':
            self.root.ids['special_'+spec.lower()].text = str(pc.special[spec])
            self.root.ids['points_left'].text = str(pc.special_points)
        #skills
        self.root.ids.skill_points.text = 'Skill Points: '+str(pc.skill_points)
        for name, value in pc.skill.items():
            self.root.ids[name].text = str(value)
            #books
            if name not in ('speech', 'gambling'):
                for i in range(1, 11):
                    number_read = 0
                    if name in pc.read_books:
                        number_read = pc.read_books[name]
                    if i <= number_read:
                        self.root.ids['book_'+str(i)+'_'+name].state = 'down'
                        self.root.ids['book_'+str(i)+'_'+name].disabled = True
                    else:
                        self.root.ids['book_'+str(i)+'_'+name].state = 'normal'
                        self.root.ids['book_'+str(i)+'_'+name].disabled = False
        #traits
        for trait_id in self.known_traits:
            if trait_id in pc.traits:
                self.root.ids['trait_'+trait_id].state = 'down'
            else:
                self.root.ids['trait_'+trait_id].state = 'normal'
            if pc.level != 1:
                self.root.ids['trait_'+trait_id].disabled = True
        #perks
        for perk_dict in (self.known_perks, self.known_perks_support, self.known_perks_class):
            for perk_id in perk_dict:
                self.root.ids['perk_'+perk_id].disabled = True
                if perk_id in pc.perks:
                    self.root.ids['perk_'+perk_id].state = 'down'
                    if pc.perks[perk_id] == pc.level and perk_id not in self.known_perks_class:
                        self.root.ids['perk_'+perk_id].disabled = False
                else:
                    self.root.ids['perk_'+perk_id].state = 'normal'
        self._update_perks()
        #drugs
        #for cannibal disable normal drugs, enable cannibal drugs
        self._toggle_cannibal_drugs()
        for drug_id in self.known_drugs:
            prefix='drug_'
            num_drugs= len(pc.drugs)
            if 'cannibal' in pc.traits:
                prefix='cannibal_drug_'
            if drug_id in pc.drugs:
                self.root.ids[prefix+drug_id].state = 'down'
            elif num_drugs >= pc.max_drugs:
                if prefix+drug_id in self.root.ids:
                    self.root.ids[prefix+drug_id].disabled = True
        #implants
        for widget_id, widget in self.root.ids.items():
            if widget_id.startswith('implant_'):
                widget.disabled = True
                widget.state = 'normal'
        for spec, value in pc.implants_special.items():
            for i in range(1, value+1):
                button = self.root.ids['implant_special_'+str(i)+'_'+spec]
                button.state = 'down'
        for implant_id, value in pc.implants.items():
            for i in range(1, value+1):
                button = self.root.ids['implant_'+implant_id+'_'+str(i)]
                button.state = 'down'
        self.enable_implants()
        self.refresh_mode = False
        self.update_stats()
        if pc.level == 1:
            #enable special +/-
            for widget in self.root.ids.special_grid.children:
                if isinstance(widget, Button):
                    widget.disabled = False
            #enable traits
            for trait_id in self.known_traits:
                if len(pc.traits)<2:
                    self.root.ids['trait_'+trait_id].disabled = False
                    if trait_id in pc.traits:
                        self.root.ids['trait_'+trait_id].state = 'down'
                    else:
                        self.root.ids['trait_'+trait_id].state = 'normal'
                else:
                    if trait_id in pc.traits:
                        self.root.ids['trait_'+trait_id].state = 'down'
                        self.root.ids['trait_'+trait_id].disabled = False
                    else:
                        self.root.ids['trait_'+trait_id].state = 'normal'
                        self.root.ids['trait_'+trait_id].disabled = True
            #disable drugs, books, implants tab
            self.root.ids.drugs_book_implant_tab.disabled = True
            #disable skill +/-
            for widget in self.root.ids.skill_grid.children:
                if isinstance(widget, Button):
                    widget.disabled = True
            #disable level down
            self.root.ids.level_restore.disabled = True
        else:
            #enable implants
            if pc.level>= 30:
                self.enable_implants()
            #disable special +/-
            for widget in self.root.ids.special_grid.children:
                if isinstance(widget, Button):
                    widget.disabled = True
            #disable traits
            for trait_id in self.known_traits:
                self.root.ids['trait_'+trait_id].disabled = True
            #enable level down
            self.root.ids.level_restore.disabled = False
            #enable level up
            self.root.ids.level_up.disabled = False
            self.root.ids.level_up_all.disabled = False
            #enable drugs, books, implants tab
            self.root.ids.drugs_book_implant_tab.disabled = False
            #enable skill +/-
            for widget in self.root.ids.skill_grid.children:
                if isinstance(widget, Button):
                    widget.disabled = False

    def level_restore(self):
        '''Remove level (or load it from history)'''
        global pc #evil global, such unpythonic, much panic, wow!
        pc = self.level_history.pop()
        self.refresh_all()


    def level_up(self, to_perk=False):
        '''Add level, if to_perk is True the function will call itself until a perk point is given. '''
        if self.refresh_mode:
            return
        #print('level up', pc.level)
        #check if we have unused perk points and if this level-up gives a perk
        if pc.level < 25:
            if pc.perk_points > 0 and (pc.level+1)%pc.perk_every_levels == 0:
                #print('use perk')
                return
        if pc.level == 30 and pc.perk_points > 0:
            return
        #save a copy of the stats
        self.level_history.append(deepcopy(pc))
        # first level up
        if pc.level == 1:
            #disable special +/-
            for widget in self.root.ids.special_grid.children:
                if isinstance(widget, Button):
                    widget.disabled = True
            #disable traits
            for trait_id in self.known_traits:
                self.root.ids['trait_'+trait_id].disabled = True
            #enable drugs, books, implants tab
            self.root.ids.drugs_book_implant_tab.disabled = False
            #for cannibal disable normal drugs, enable cannibal drugs
            self._toggle_cannibal_drugs()
            #enable skill +/-
            for widget in self.root.ids.skill_grid.children:
                if isinstance(widget, Button):
                    widget.disabled = False
            #enable level down
            self.root.ids.level_restore.disabled = False
        #give level
        pc.level += 1
        #give hp
        if pc.level<= 29:
            if pc.special.E%2 == 1 and pc.level%2 == 1:
                pc.hit_points+=1
            pc.hit_points+= pc.special.E//2
        elif pc.level < 100 and pc.level%2 == 0:
                pc.hit_points+=1
        #enable implants
        if pc.level>= 30:
            self.enable_implants()
        #give skill points:
        if 'gifted' in pc.traits:
            pc.skill_points += pc.special.I
        else:
            pc.skill_points += 5+pc.special.I*3
        pc.skill_points += pc.bonus_skill_points
        #update skill points display
        self.root.ids.skill_points.text = 'Skill Points: '+str(pc.skill_points)
        #reset minimum for read books
        self.min_skill_level={}
        #give perk points
        if pc.level<=24:
            if pc.level%pc.perk_every_levels == 0:
                pc.perk_points = 1
        self._update_perks()
        #disable un-taking perks from the last level
        for perk_id in pc.perks:
            self.root.ids['perk_'+perk_id].disabled = True
        #update level label
        self.root.ids.level_label.text = 'Level: '+str(pc.level)
        #update stats
        self.update_stats()
        #level up to next perk or class perk level
        if to_perk:
            if pc.level>120:
                return
            if pc.level not in (30, 40, 50, 60, 80, 100, 110, 120):
                #print('multi level up', pc.level)
                self.level_up(to_perk)

    def add_special(self, spec, amount):
        '''Called when +/- is pressed on the special tab.
        spec in ['S','P','E','C','I','A','L']
        amout either 1 or -1
        '''
        if self.refresh_mode:
            return
        # +
        if amount > 0:
            if pc.special_points > 0:
                if pc.special[spec] < pc.max_special:
                    pc.special_points-=1
                    pc.special[spec]+=1
        else: # -
            if pc.special[spec] > pc.min_special:
                pc.special_points+=1
                pc.special[spec]-=1
        #update labels
        self._update_special()

if __name__ == '__main__':
    PlanerApp().run()

