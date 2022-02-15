# -*- coding: utf-8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

from resources.lib import process
import sys
from typing import Dict, List, Optional

from kutils import addon
from kutils import utils

def pass_list_to_skin(name, data, prefix="", limit: Optional[int]=False) -> None:
    """Set home window properties from the data

    SetProperty(prefixname.%d.data_item key,data_item value, home) for 1 to 
    limit number of items in data 

    Args:
        name (str): Type of data being returned.  Used to construct
            the skin window property key eg. topratedmovies from invocation
            parameter info=
        data (kutils.itemlist.ItemList): collection of ListItems 
            (Video or Audio)
        prefix (str, optional):  Optional prefix for the name.  Defaults to "".
        limit (int, optional):  Number of items to return. Defaults to False.

    Returns:
        None
    """
    #utils.log('type name: {} type data: {}'.format(type(name), type(data)))
    #utils.log('dir data{}'.format(dir(data)))
    if data and limit and int(limit) < len(data):
        data = data[:int(limit)]
    if not data:
        addon.set_global('%s%s.Count' % (prefix, name), '0')
        return None
    for (count, result) in enumerate(data):
        for (key, value) in result.get_infos().items():
            addon.set_global('%s%s.%i.%s' %
                             (prefix, name, count + 1, key), str(value))
        for key, value in result.get("properties", {}).items():
            if not value:
                continue
            addon.set_global('%s%s.%i.%s' %
                             (prefix, name, count + 1, key), str(value))
    addon.set_global('%s%s.Count' % (prefix, name), str(len(data)))


class Main:

    def __init__(self):
        """Provides the main process when called by RunScript.

        Parse the invocation argument strings to create self.infos (called with
        info= args) list and self.params dict  (called with param=value pairs)
        """
        utils.log("version {} started".format(addon.VERSION))
        addon.set_global("extendedinfo_running", "true")
        self._parse_argv()
        for info in self.infos:
            listitems = process.start_info_actions(info, self.params)
            pass_list_to_skin(name=info,
                              data=listitems,
                              prefix=self.params.get("prefix", ""),
                              limit=self.params.get("limit", 20))
        if not self.infos:
            addon.set_global('infodialogs.active', "true")
            from resources.lib.WindowManager import wm
            wm.open_video_list()
            addon.clear_global('infodialogs.active')
        addon.clear_global("extendedinfo_running")

    def _parse_argv(self) -> None:
        self.infos: List[str] = []
        self.params: Dict[str, str] = {"handle": None}
        for arg in sys.argv[1:]:
            param = arg.replace('"', '').replace("'", " ")
            if param.startswith('info='):
                self.infos.append(param[5:])
            else:
                try:
                    self.params[param.split("=")[0].lower()] = "=".join(
                        param.split("=")[1:]).strip()
                except Exception:
                    pass

if (__name__ == "__main__"):
    Main()
utils.log('finished')
