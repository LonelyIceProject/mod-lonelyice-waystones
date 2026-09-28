-- Client side of mod-lonelyice-waystones (src/waystones.cpp).
-- Server -> client: "S\t<hex>"  attunement bitmask (bit id-1).
-- Client -> server: "SYNC", "TP\t<id>" (addon whispers to self, prefix KTWS).

local PREFIX = "KTWS"
local ICON = "Interface\\Icons\\Spell_Arcane_TeleportDalaran"
local RU = GetLocale() == "ruRU"

local L = RU and {
    attuned = "Настроен. Щелчок - транслокация.",
    notAttuned = "Не настроен: коснитесь этого кристалла, чтобы открыть его.",
    notAttunedError = "Вы не настроены на этот кристалл.",
    none = "Вы ещё не настроены ни на один путевой кристалл.",
    title = "Путевые кристаллы",
    listHint = "Список открытых кристаллов. То же самое: /ways",
    offer = "%s переместился к кристаллу «%s».\nПоследовать за ним?",
    follow = "Последовать",
    stay = "Остаться",
    continents = { [14] = "Восточные королевства", [13] = "Калимдор", [466] = "Запределье", [485] = "Нордскол" },
} or {
    attuned = "Attuned. Click to translocate.",
    notAttuned = "Not attuned: touch this crystal to unlock it.",
    notAttunedError = "You are not attuned to that waycrystal.",
    none = "You are not attuned to any waycrystal yet.",
    title = "Waycrystals",
    listHint = "List of attuned crystals. Also: /ways",
    offer = "%s translocated to %s.\nFollow?",
    follow = "Follow",
    stay = "Stay",
    continents = { [14] = "Eastern Kingdoms", [13] = "Kalimdor", [466] = "Outland", [485] = "Northrend" },
}
local CONTINENT_ORDER = { 14, 13, 466, 485 }

-- KTW_DATA[id] = { zoneMap, floor, x, y, continentMap, cx, cy, name_en, name_ru, zone_en, zone_ru, inn }
local function Name(d) return RU and d[9] or d[8] end
local function ZoneName(d) return RU and d[11] or d[10] end

local attuned = {}

local function Send(msg)
    SendAddonMessage(PREFIX, msg, "WHISPER", UnitName("player"))
end

local function Translocate(id)
    if attuned[id] then
        Send("TP\t" .. id)
    else
        UIErrorsFrame:AddMessage(L.notAttunedError, 1, 0.1, 0.1)
    end
end

-- ------------------------------------------------------------------ world map pins
local pins = {}

local function PinOnEnter(pin)
    local d = KTW_DATA[pin.id]
    GameTooltip:SetOwner(pin, "ANCHOR_RIGHT")
    GameTooltip:SetText(Name(d), 0.71, 0.55, 1)
    GameTooltip:AddLine(ZoneName(d), 1, 1, 1)
    if attuned[pin.id] then
        GameTooltip:AddLine(L.attuned, 0.2, 1, 0.2, true)
    else
        GameTooltip:AddLine(L.notAttuned, 0.6, 0.6, 0.6, true)
    end
    GameTooltip:Show()
end

local function GetPin(i)
    local pin = pins[i]
    if not pin then
        pin = CreateFrame("Button", nil, WorldMapButton)
        -- Purple halo so a crystal next to an inn or flight pin still reads as its own marker
        pin.glow = pin:CreateTexture(nil, "BACKGROUND")
        pin.glow:SetTexture("Interface\\Minimap\\UI-Minimap-ZoomButton-Highlight")
        pin.glow:SetBlendMode("ADD")
        pin.glow:SetVertexColor(0.75, 0.45, 1)
        pin.glow:SetPoint("CENTER")
        pin.back = pin:CreateTexture(nil, "BORDER")
        pin.back:SetTexture("Interface\\Minimap\\UI-Minimap-Background")
        pin.back:SetVertexColor(0, 0, 0, 0.8)
        pin.back:SetPoint("TOPLEFT", -1, 1)
        pin.back:SetPoint("BOTTOMRIGHT", 1, -1)
        pin.icon = pin:CreateTexture(nil, "ARTWORK")
        pin.icon:SetAllPoints()
        SetPortraitToTexture(pin.icon, ICON)   -- the client cuts the square icon into a circle
        pin:SetHighlightTexture("Interface\\Minimap\\UI-Minimap-ZoomButton-Highlight", "ADD")
        pin:RegisterForClicks("LeftButtonUp")
        pin:SetScript("OnEnter", PinOnEnter)
        pin:SetScript("OnLeave", function() GameTooltip:Hide() end)
        pin:SetScript("OnClick", function(self) Translocate(self.id) end)
        pins[i] = pin
    end
    return pin
end

local function Refresh()
    if not KTW_DATA or not WorldMapButton:IsVisible() then
        return
    end

    -- The 3.3.5 client reports WorldMapArea.dbc ids plus one (DragonUI subtracts it too)
    local mapID = GetCurrentMapAreaID() - 1
    local floor = GetCurrentMapDungeonLevel()
    local w, h = WorldMapButton:GetWidth(), WorldMapButton:GetHeight()
    -- Well above DragonUI's inn/flight pins (+2), which sit on nearly the same spot
    local level = WorldMapButton:GetFrameLevel() + 20
    local n = 0

    for id, d in pairs(KTW_DATA) do
        local x, y, size
        if d[1] == mapID and (d[2] == 0 or d[2] == floor) then
            x, y, size = d[3], d[4], 20
        elseif d[5] == mapID then
            x, y, size = d[6], d[7], 13
        end
        if x then
            n = n + 1
            local pin = GetPin(n)
            pin.id = id
            pin:SetSize(size, size)
            pin.glow:SetSize(size * 1.7, size * 1.7)
            if attuned[id] then pin.glow:Show() else pin.glow:Hide() end
            pin:SetFrameLevel(level)
            pin:ClearAllPoints()
            pin:SetPoint("CENTER", WorldMapButton, "TOPLEFT", x * w, -y * h)
            pin.icon:SetDesaturated(not attuned[id])
            pin:SetAlpha(attuned[id] and 1 or 0.65)
            pin:Show()
        end
    end

    for i = n + 1, #pins do
        pins[i]:Hide()
    end

    if KirinTorWaystonesMapButton then
        KirinTorWaystonesMapButton:SetFrameLevel(level + 5)
    end
end

-- ------------------------------------------------------------------ /ways list (continent > zone > crystal)
local menuFrame = CreateFrame("Frame", "KirinTorWaystonesMenu", UIParent, "UIDropDownMenuTemplate")

local function BuildMenu()
    local byContinent = {}
    for id, d in pairs(KTW_DATA) do
        if attuned[id] then
            local zones = byContinent[d[5]] or {}
            byContinent[d[5]] = zones
            local zone = ZoneName(d)
            zones[zone] = zones[zone] or {}
            table.insert(zones[zone], id)
        end
    end

    local menu = { { text = L.title, isTitle = true, notCheckable = true } }
    for _, cont in ipairs(CONTINENT_ORDER) do
        local zones = byContinent[cont]
        if zones then
            local zoneNames = {}
            for zone in pairs(zones) do table.insert(zoneNames, zone) end
            table.sort(zoneNames)

            local zoneMenu = {}
            for _, zone in ipairs(zoneNames) do
                local ids = zones[zone]
                table.sort(ids, function(a, b) return Name(KTW_DATA[a]) < Name(KTW_DATA[b]) end)
                local stoneMenu = {}
                for _, id in ipairs(ids) do
                    table.insert(stoneMenu, { text = Name(KTW_DATA[id]), notCheckable = true,
                        func = function() CloseDropDownMenus(); Translocate(id) end })
                end
                table.insert(zoneMenu, { text = zone, notCheckable = true, hasArrow = true, menuList = stoneMenu })
            end
            table.insert(menu, { text = L.continents[cont], notCheckable = true, hasArrow = true, menuList = zoneMenu })
        end
    end
    return menu, next(byContinent) ~= nil
end

local function ShowMenu()
    local menu, any = BuildMenu()
    if not any then
        DEFAULT_CHAT_FRAME:AddMessage("|cffb48cff" .. L.none .. "|r")
        UIErrorsFrame:AddMessage(L.none, 0.71, 0.55, 1)
        return
    end
    EasyMenu(menu, menuFrame, "cursor", 0, 0, "MENU")
end

SLASH_KIRINTORWAYSTONES1 = "/ways"
SLASH_KIRINTORWAYSTONES2 = "/waystones"
SlashCmdList.KIRINTORWAYSTONES = ShowMenu

-- List button in the map's top-left corner (DragonUI keeps its controls top-right)
local mapButton = CreateFrame("Button", "KirinTorWaystonesMapButton", WorldMapButton)
mapButton:SetSize(30, 30)
mapButton:SetPoint("TOPLEFT", WorldMapButton, "TOPLEFT", 10, -10)
mapButton.icon = mapButton:CreateTexture(nil, "ARTWORK")
mapButton.icon:SetAllPoints()
mapButton.icon:SetTexture(ICON)
mapButton.icon:SetTexCoord(0.08, 0.92, 0.08, 0.92)
mapButton.border = mapButton:CreateTexture(nil, "OVERLAY")
mapButton.border:SetTexture("Interface\\Buttons\\UI-ActionButton-Border")
mapButton.border:SetBlendMode("ADD")
mapButton.border:SetVertexColor(0.75, 0.45, 1)
mapButton.border:SetSize(58, 58)
mapButton.border:SetPoint("CENTER")
mapButton:SetHighlightTexture("Interface\\Buttons\\ButtonHilight-Square", "ADD")
mapButton:SetScript("OnClick", ShowMenu)
mapButton:SetScript("OnEnter", function(self)
    GameTooltip:SetOwner(self, "ANCHOR_RIGHT")
    GameTooltip:SetText(L.title, 0.71, 0.55, 1)
    GameTooltip:AddLine(L.listHint, 1, 1, 1, true)
    GameTooltip:Show()
end)
mapButton:SetScript("OnLeave", function() GameTooltip:Hide() end)

-- ------------------------------------------------------------------ group follow offer
-- Server: "OFFER\t<id>\t<name>" when a party member translocates to a crystal we are attuned to.
StaticPopupDialogs["KTWS_OFFER"] = {
    text = L.offer,
    button1 = L.follow,
    button2 = L.stay,
    OnAccept = function(self, data)
        Translocate(data)
    end,
    timeout = 60,
    whileDead = false,
    hideOnEscape = true,
}

local function ShowOffer(arg)
    local id, who = arg:match("^(%d+)\t(.*)$")
    id = tonumber(id)
    local d = id and KTW_DATA and KTW_DATA[id]
    if not d then
        return
    end
    StaticPopup_Hide("KTWS_OFFER")
    local dialog = StaticPopup_Show("KTWS_OFFER", who, Name(d))
    if dialog then
        dialog.data = id
    end
end

-- ------------------------------------------------------------------ events
local events = CreateFrame("Frame")
local syncAt

events:SetScript("OnEvent", function(_, event, prefix, msg, _, sender)
    if event == "CHAT_MSG_ADDON" then
        if prefix ~= PREFIX or sender ~= UnitName("player") then
            return
        end
        local cmd, arg = msg:match("^(%a+)\t?(.*)$")
        if cmd == "S" then
            wipe(attuned)
            for i = 1, #arg do
                local nibble = tonumber(arg:sub(i, i), 16) or 0
                for b = 0, 3 do
                    if bit.band(nibble, bit.lshift(1, b)) ~= 0 then
                        attuned[(i - 1) * 4 + b + 1] = true
                    end
                end
            end
            Refresh()
        elseif cmd == "OFFER" then
            ShowOffer(arg)
        end
    elseif event == "PLAYER_ENTERING_WORLD" then
        syncAt = GetTime() + 2
    elseif event == "WORLD_MAP_UPDATE" then
        Refresh()
    end
end)
events:RegisterEvent("CHAT_MSG_ADDON")
events:RegisterEvent("PLAYER_ENTERING_WORLD")
events:RegisterEvent("WORLD_MAP_UPDATE")

-- The server may not be ready for addon traffic the instant the world loads
events:SetScript("OnUpdate", function()
    if syncAt and GetTime() >= syncAt then
        syncAt = nil
        Send("SYNC")
    end
end)

WorldMapButton:HookScript("OnShow", Refresh)
-- DragonUI redraws its pins from WorldMapFrame_Update; re-level ours after it
hooksecurefunc("WorldMapFrame_Update", Refresh)
WorldMapButton:HookScript("OnSizeChanged", Refresh)
