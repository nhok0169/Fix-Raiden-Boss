#make by NK#1321 if have error don't Dm im lazy. and thank silent or who for the script under
import bpy
import itertools
#rename raiden vg to reiden boss vg
name_list = [
['0','0'],
['1','1'],
['2','2'],
['3','3'],
['4','4'],
['5','5'],
['6','6'],
['7','7'],
['8','60'],
['9','61'],
['10','66'],
['11','67'],
['12','8'],
['13','9'],
['14','10'],
['15','11'],
['16','12'],
['17','13'],
['18','14'],
['19','15'],
['20','16'],
['21','17'],
['22','18'],
['23','19'],
['24','20'],
['25','21'],
['26','22'],
['27','23'],
['28','24'],
['29','25'],
['30','26'],
['31','27'],
['32','28'],
['33','29'],
['34','30'],
['35','31'],
['36','32'],
['37','33'],
['38','34'],
['39','35'],
['40','36'],
['41','37'],
['42','38'],
['43','39'],
['44','40'],
['45','41'],
['46','42'],
['47','94'],
['48','43'],
['49','44'],
['50','45'],
['51','46'],
['52','47'],
['53','48'],
['54','49'],
['55','50'],
['56','51'],
['57','52'],
['58','53'],
['59','54'],
['60','55'],
['61','56'],
['62','57'],
['63','58'],
['64','59'],
['65','114'],
['66','116'],
['67','115'],
['68','117'],
['69','74'],
['70','62'],
['71','64'],
['72','106'],
['73','108'],
['74','110'],
['75','75'],
['76','77'],
['77','79'],
['78','87'],
['79','89'],
['80','91'],
['81','95'],
['82','97'],
['83','99'],
['84','81'],
['85','83'],
['86','85'],
['87','68'],
['88','70'],
['89','72'],
['90','104'],
['91','112'],
['92','93'],
['93','63'],
['94','65'],
['95','107'],
['96','109'],
['97','111'],
['98','76'],
['99','78'],
['100','80'],
['101','88'],
['102','90'],
['103','92'],
['104','96'],
['105','98'],
['106','100'],
['107','82'],
['108','84'],
['109','86'],
['110','69'],
['111','71'],
['112','73'],
['113','105'],
['114','113'],
['115','101'],
['116','102'],
['117','103'],
]

nhok0169 = bpy.context.active_object.vertex_groups
for n in name_list:
    if n[0] in nhok0169:
        nhok0169[n[0]].name = n[1]
#stolen from silent merge script bc im stupid in python
class Fatal(Exception): pass
selected_obj = [obj for obj in bpy.context.selected_objects]
vgroup_names = []
smallest_group_number = 000
largest_group_number = 999
vgroup_names = [[f"{i}" for i in range(smallest_group_number, largest_group_number+1)]]

if not vgroup_names:
    raise Fatal("No vertex groups found, please double check an object is selected and required data has been entered")

for cur_obj, cur_vgroup in zip(selected_obj, itertools.cycle(vgroup_names)):
    for vname in cur_vgroup:
        relevant = [x.name for x in cur_obj.vertex_groups if x.name.split(".")[0] == f"{vname}"]

        if relevant:

            vgroup = cur_obj.vertex_groups.new(name=f"x{vname}")
                
            for vert_id, vert in enumerate(cur_obj.data.vertices):
                available_groups = [v_group_elem.group for v_group_elem in vert.groups]
                
                combined = 0
                for v in relevant:
                    if cur_obj.vertex_groups[v].index in available_groups:
                        combined += cur_obj.vertex_groups[v].weight(vert_id)

                if combined > 0:
                    vgroup.add([vert_id], combined ,'ADD')
                    
            for vg in [x for x in cur_obj.vertex_groups if x.name.split(".")[0] == f"{vname}"]:
                cur_obj.vertex_groups.remove(vg)

            for vg in cur_obj.vertex_groups:
                if vg.name[0].lower() == "x":
                    vg.name = vg.name[1:]
                    
    bpy.context.view_layer.objects.active = cur_obj
#sort vg
nhok_0169 = bpy.ops.object.vertex_group_sort(sort_type='NAME')
