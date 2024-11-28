# Mutex bot

Telegram bot to simplify group use of exclusive resources.


## Usage

- [ ] `/set COMMAND` - manage sets of resources
    - [ ] `add SET_NAME` - add new set with `SET_NAME` as a name and return `set_id` to share
    - [ ] `del SET_ID` - delete set (available only for set owner)
    - [ ] `list` - list all available sets
    - [ ] `default SET_ID` - makes set `SET_ID` as default set
    - [ ] `subscribe [--user=USER_ID] SET_ID` - request subscription for set `SET_ID` (if `USER_ID` is not specified) 
    or add subscription for user `USER_ID` to set `SET_ID` (if current user id owner of set `SET_ID` and user `USER_ID` specified)
    - [ ] `confirm [--set=SET_ID] USER_ID` - confirm subscription to set `SET_ID` (to default set if missed) for user `USER_ID` 
    - [ ] `decline [--set=SET_ID] USER_ID` - decline subscription to set `SET_ID` (to default set if missed) for user `USER_ID` 
    - [ ] `users [--set=SET_ID] [--requested|--confirmed|--declined]` - show list of users, related to set `SET_ID` (to default set if missed)
- [ ] `/group COMMAND [OPTIONS]` - manage groups of resources
    - [ ] `add [--set=SET_ID] [--group=GROUP_ID] GROUP_NAME`
    - [ ] `list`
    - [ ] `default GROUP_ID` - set group with `GROUP_ID` as default for all operations that required group
    (if none of it is specified for operation default group will be used)
- [ ] `/resource` - manage resources (in specified or default group)
    - [ ] `add [--set=SET_ID] [--group=GROUP_ID] NAME` - add new resource to the group
    - [ ] `list [--set=SET_ID] [--group=GROUP_ID]` - list all existed resources of the group with their `RESOURCE_ID`
    - [ ] `del RESOURCE_ID` - delete resource `RESOURCE_ID`
    - [ ] `config RESOURCE_ID setting=value` - manage settings of the resources `RESOURCE_ID`
        - [ ] `auto-release-timeout=SECONDS` - set up timeout before automatically releasing the resource
        - [ ] `remind-timeout=SECONDS` - reminds user to release the resource every `SECONDS` seconds after acquiring it
- [ ] `/config` - user configs
    - [ ] `auto-release-timeout=SECONDS` - set up timeout before automatically releasing any acquired resource 
    (can be overridden by config of the `resource`)
    - [ ] `remind-timeout=SECONDS` - reminds user to release any resource every `SECONDS` seconds after acquiring it


## Data model

- User
    - user_id
    - user_name
- ResourceSet
    - set_id
    - set_name
    - set_pin
    - owner_user_id
- Resource
    - resource_id
    - resource_name
    - is_group
    - set_id
- ResourceUsingHistory
    - resource_id
    - user_id
    - acquired
    - released
- Subscription
    - user_id
    - set_id
    - requested
    - confirmed
    - declined
- UserConfig
    - user_id
    - config_key
    - config_value
- ResourceConfig
    - resource_id
    - config_key
    - config_value
