# Mutex bot

Telegram bot to simplify group use of exclusive resources.


## Usage

- [ ]`/group command [options]` - manage groups of resources
    - [ ] `add [--parent-group=GROUP_ID] GROUP_NAME`
    - [ ] `list`
    - [ ] `default GROUP_ID` - set group with `GROUP_ID` as default for all operations that required group
    (if none of it is specified for operation default group will be used)
- [ ] `/resource` - manage resources (in specified or default group)
    - [ ] `add [--group=GROUP_ID] NAME` - add new resource to the group
    - [ ] `list [--group=GROUP_ID]` - list all existed resources of the group with their `RESOURCE_ID`
    - [ ] `del RESOURCE_ID` - delete resource `RESOURCE_ID` from the group
    - [ ] `config RESOURCE_ID setting=value` - manage settings of the resources `RESOURCE_ID`
        - [ ] `auto-release-timeout=SECONDS` - set up timeout before automaticly releasing the resource
        - [ ] `remind-timeout=SECONDS` - reminds user to release the resource every SECONDS seconds after acquiring it
- [ ] `/config` - user configs
    - [ ] `auto-release-timeout=SECONDS` - set up timeout before automaticly releasing any acuired resource (can be overriden by config of the `resource`)
    - [ ] `remind-timeout=SECONDS` - reminds user to release any resource every SECONDS seconds after acquiring it


## Data model

- User
    - user_id
    - user_name
- ResourceGroup
    - resource_group_id
    - resource_group_name
- Resource
- ResourceUser
- UserConfig
- ResourceConfig
