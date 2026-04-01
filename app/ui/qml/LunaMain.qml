import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Window 2.15

ApplicationWindow {
    id: root
    width: 1600
    height: 960
    minimumWidth: 1240
    minimumHeight: 760
    visible: true
    title: pageTitle() + " - LunaAI"
    color: "#060606"

    property bool sidebarExpanded: true
    property int currentPage: 0
    property string contextSessionId: ""
    property string contextSessionTitle: ""

    function pageTitle() {
        if (currentPage === 0) return lunaBridge.currentChatTitle
        if (currentPage === 1) return "Gallery"
        if (currentPage === 2) return "Projects"
        if (currentPage === 3) return "Applications"
        if (currentPage === 4) return "Updates"
        if (currentPage === 5) return "Friends / Groups"
        return "Settings"
    }

    Rectangle {
        anchors.fill: parent
        color: "#060606"

        Rectangle {
            anchors.fill: parent
            color: "#090909"
            opacity: 0.88
        }

        Rectangle {
            width: parent.width * 0.38
            height: parent.height * 0.56
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.topMargin: -80
            anchors.rightMargin: -60
            radius: width / 2
            color: "#ffffff"
            opacity: 0.03
        }

        Rectangle {
            width: parent.width * 0.26
            height: parent.height * 0.4
            anchors.left: parent.left
            anchors.bottom: parent.bottom
            anchors.leftMargin: -100
            anchors.bottomMargin: -120
            radius: width / 2
            color: "#ffffff"
            opacity: 0.02
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 16
            spacing: 12

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 74
                radius: 24
                color: "#101010"
                border.color: "#1f1f1f"

                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 14
                    spacing: 14

                    Button {
                        id: sidebarToggle
                        Layout.preferredWidth: 42
                        Layout.preferredHeight: 42
                        text: sidebarExpanded ? "<" : ">"
                        onClicked: sidebarExpanded = !sidebarExpanded
                        background: Rectangle {
                            radius: 14
                            color: parent.down ? "#202020" : "#151515"
                            border.color: "#262626"
                        }
                        contentItem: Text {
                            text: sidebarToggle.text
                            color: "#f4f4f4"
                            font.pixelSize: 20
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                    }

                    Rectangle {
                        Layout.preferredWidth: 44
                        Layout.preferredHeight: 44
                        radius: 22
                        color: "#0d0d0d"
                        border.color: "#2b2b2b"

                        Item {
                            anchors.centerIn: parent
                            width: 26
                            height: 26

                            Rectangle { width: 26; height: 26; radius: 13; color: "#d7d7d7"; opacity: 0.08 }
                            Rectangle { width: 18; height: 18; radius: 9; anchors.centerIn: parent; color: "#ffffff"; opacity: 0.1 }
                            Rectangle { width: 10; height: 10; radius: 5; anchors.centerIn: parent; color: "#ffffff"; opacity: 0.82 }
                            Rectangle { width: 9; height: 3; radius: 2; anchors.horizontalCenter: parent.horizontalCenter; anchors.top: parent.top; anchors.topMargin: 6; color: "#ffffff"; opacity: 0.3 }
                        }
                    }

                    ColumnLayout {
                        spacing: 1
                        Text { text: "LunaAI"; color: "#f8f8f8"; font.pixelSize: 20; font.weight: Font.DemiBold }
                        Text { text: "Black box intelligence. Clean visible control."; color: "#8b8b8f"; font.pixelSize: 11 }
                    }

                    Item { Layout.fillWidth: true }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.maximumWidth: 380
                        Layout.preferredHeight: 42
                        radius: 16
                        color: "#0f0f0f"
                        border.color: "#1e1e1e"
                        Text {
                            anchors.fill: parent
                            anchors.leftMargin: 16
                            anchors.rightMargin: 16
                            verticalAlignment: Text.AlignVCenter
                            color: "#a3a3a8"
                            elide: Text.ElideRight
                            text: lunaBridge.statusText
                            font.pixelSize: 12
                        }
                    }

                    Button {
                        id: profileButton
                        Layout.preferredHeight: 44
                        Layout.preferredWidth: 196
                        onClicked: profilePopup.open()
                        background: Rectangle { radius: 18; color: "#121212"; border.color: "#242424" }
                        contentItem: RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 12
                            anchors.rightMargin: 12
                            spacing: 10
                            Rectangle {
                                Layout.preferredWidth: 28
                                Layout.preferredHeight: 28
                                radius: 14
                                color: "#1b1b1b"
                                border.color: "#2b2b2b"
                                clip: true
                                Image { anchors.fill: parent; source: lunaBridge.profileImagePath; fillMode: Image.PreserveAspectCrop; visible: source !== "" }
                                Text { anchors.centerIn: parent; visible: lunaBridge.profileImagePath === ""; text: lunaBridge.profileName.length > 0 ? lunaBridge.profileName.charAt(0).toUpperCase() : "L"; color: "#f5f5f5"; font.pixelSize: 12; font.weight: Font.DemiBold }
                            }
                            ColumnLayout {
                                spacing: 0
                                Layout.fillWidth: true
                                Text { text: lunaBridge.profileName; color: "#f5f5f5"; font.pixelSize: 13; elide: Text.ElideRight }
                                Text { text: "System profile"; color: "#7f7f84"; font.pixelSize: 10 }
                            }
                        }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 12
                Rectangle {
                    id: sidebarPanel
                    Layout.preferredWidth: sidebarExpanded ? 300 : 92
                    Layout.fillHeight: true
                    radius: 28
                    color: "#101010"
                    border.color: "#1c1c1c"
                    clip: true

                    Behavior on Layout.preferredWidth {
                        NumberAnimation { duration: 220; easing.type: Easing.InOutQuad }
                    }

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 12

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 44
                            radius: 16
                            color: "#0d0d0d"
                            border.color: "#1d1d1d"
                            visible: sidebarExpanded
                            TextField {
                                anchors.fill: parent
                                anchors.leftMargin: 14
                                anchors.rightMargin: 14
                                placeholderText: "Search"
                                color: "#f4f4f4"
                                placeholderTextColor: "#68686e"
                                selectByMouse: true
                                background: null
                                onTextChanged: lunaBridge.setChatSearchQuery(text)
                            }
                        }

                        Button {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 48
                            onClicked: { lunaBridge.createNewChat(); currentPage = 0 }
                            background: Rectangle { radius: 18; color: "#f5f5f5" }
                            contentItem: Text {
                                text: sidebarExpanded ? "+  New Chat" : "+"
                                color: "#111111"
                                font.pixelSize: 14
                                font.weight: Font.DemiBold
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                            }
                        }

                        Repeater {
                            model: [
                                { label: "Gallery", page: 1 },
                                { label: "Projects", page: 2 },
                                { label: "Applications", page: 3 },
                                { label: "Updates", page: 4 },
                                { label: "Friends / Groups", page: 5 }
                            ]
                            delegate: Button {
                                required property var modelData
                                Layout.fillWidth: true
                                Layout.preferredHeight: 42
                                onClicked: currentPage = modelData.page
                                background: Rectangle {
                                    radius: 16
                                    color: currentPage === modelData.page ? "#171717" : "transparent"
                                    border.color: currentPage === modelData.page ? "#2a2a2a" : "#161616"
                                }
                                contentItem: Text {
                                    text: sidebarExpanded ? modelData.label : modelData.label.charAt(0)
                                    color: currentPage === modelData.page ? "#f5f5f5" : "#a4a4aa"
                                    font.pixelSize: 13
                                    horizontalAlignment: Text.AlignHCenter
                                    verticalAlignment: Text.AlignVCenter
                                    elide: Text.ElideRight
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            radius: 22
                            color: "#0c0c0c"
                            border.color: "#191919"
                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 12
                                spacing: 10
                                Text { text: sidebarExpanded ? "Chats" : "C"; color: "#737379"; font.pixelSize: 11; font.weight: Font.Medium }
                                ListView {
                                    id: chatListView
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    model: lunaBridge.chatsModel
                                    clip: true
                                    spacing: 8
                                    delegate: Rectangle {
                                        required property string sessionId
                                        required property string title
                                        required property bool pinned
                                        width: chatListView.width
                                        height: 54
                                        radius: 18
                                        color: lunaBridge.currentChatTitle === title ? "#1b1b1b" : "#111111"
                                        border.color: lunaBridge.currentChatTitle === title ? "#303030" : "#1c1c1c"
                                        RowLayout {
                                            anchors.fill: parent
                                            anchors.leftMargin: 14
                                            anchors.rightMargin: 14
                                            spacing: 10
                                            Rectangle { Layout.preferredWidth: 8; Layout.preferredHeight: 8; radius: 4; visible: pinned; color: "#ffffff"; opacity: 0.9 }
                                            Text { Layout.fillWidth: true; text: sidebarExpanded ? title : title.charAt(0); color: "#f1f1f1"; elide: Text.ElideRight; font.pixelSize: 13 }
                                        }
                                        MouseArea {
                                            anchors.fill: parent
                                            acceptedButtons: Qt.LeftButton | Qt.RightButton
                                            onClicked: function(mouse) {
                                                if (mouse.button === Qt.RightButton) {
                                                    root.contextSessionId = sessionId
                                                    root.contextSessionTitle = title
                                                    chatMenu.popup()
                                                } else {
                                                    lunaBridge.switchChat(sessionId)
                                                    currentPage = 0
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        Item { Layout.fillHeight: true }
                        Button {
                            Layout.alignment: Qt.AlignHCenter
                            Layout.preferredWidth: sidebarExpanded ? 110 : 42
                            Layout.preferredHeight: 42
                            onClicked: currentPage = 6
                            background: Rectangle { radius: 16; color: currentPage === 6 ? "#171717" : "#121212"; border.color: "#242424" }
                            contentItem: Text { text: sidebarExpanded ? "Settings" : "S"; color: "#f2f2f2"; font.pixelSize: 13; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    radius: 32
                    color: "#0b0b0b"
                    border.color: "#1b1b1b"

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 18
                        spacing: 16

                        RowLayout {
                            Layout.fillWidth: true
                            ColumnLayout {
                                spacing: 2
                                Text { text: root.pageTitle(); color: "#fafafa"; font.pixelSize: 26; font.weight: Font.DemiBold }
                                Text { text: currentPage === 0 ? "Minimal AI conversation and execution workspace." : "System layer organized for clean long-term work."; color: "#7f7f86"; font.pixelSize: 12 }
                            }
                            Item { Layout.fillWidth: true }
                            Rectangle {
                                radius: 18
                                color: "#111111"
                                border.color: "#222222"
                                implicitWidth: 250
                                implicitHeight: 44
                                Text { anchors.centerIn: parent; text: lunaBridge.currentProjectTitle === "No project selected" ? "No active project" : lunaBridge.currentProjectTitle; color: "#cfcfd4"; font.pixelSize: 12 }
                            }
                        }

                        StackLayout {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            currentIndex: currentPage
                            Item {
                                ColumnLayout {
                                    anchors.fill: parent
                                    spacing: 16
                                    Rectangle {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: lunaBridge.hasMessages() ? 116 : 210
                                        radius: 28
                                        color: "#0f0f0f"
                                        border.color: "#1c1c1c"
                                        RowLayout {
                                            anchors.fill: parent
                                            anchors.margins: 18
                                            spacing: 20
                                            Item {
                                                Layout.preferredWidth: lunaBridge.hasMessages() ? 80 : 160
                                                Layout.preferredHeight: lunaBridge.hasMessages() ? 80 : 160
                                                Rectangle { anchors.centerIn: parent; width: parent.width; height: parent.height; radius: width / 2; color: "#ffffff"; opacity: 0.04 }
                                                Rectangle { anchors.centerIn: parent; width: parent.width * 0.74; height: width; radius: width / 2; color: "#f2f2f2"; opacity: 0.08 }
                                                Rectangle { anchors.centerIn: parent; width: parent.width * 0.45; height: width; radius: width / 2; color: "#ffffff"; opacity: 0.82 }
                                                Rectangle { anchors.horizontalCenter: parent.horizontalCenter; anchors.top: parent.top; anchors.topMargin: parent.height * 0.18; width: parent.width * 0.22; height: parent.height * 0.06; radius: height / 2; color: "#ffffff"; opacity: 0.26 }
                                            }
                                            ColumnLayout {
                                                Layout.fillWidth: true
                                                spacing: 6
                                                Text { text: "LunaAI"; color: "#fbfbfb"; font.pixelSize: lunaBridge.hasMessages() ? 24 : 34; font.weight: Font.DemiBold }
                                                Text {
                                                    text: lunaBridge.hasMessages() ? "System conversation remains clean, contextual, and ready for execution." : "A calm AI control surface for Luna, Xeno, and the execution layer."
                                                    color: "#8f8f95"
                                                    wrapMode: Text.WordWrap
                                                    font.pixelSize: 13
                                                    Layout.maximumWidth: 680
                                                }
                                            }
                                        }
                                    }

                                    Rectangle {
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true
                                        radius: 28
                                        color: "#101010"
                                        border.color: "#1c1c1c"
                                        ListView {
                                            id: messageView
                                            anchors.fill: parent
                                            anchors.margins: 20
                                            model: lunaBridge.messagesModel
                                            spacing: 14
                                            clip: true
                                            delegate: Item {
                                                required property string role
                                                required property string author
                                                required property string content
                                                width: messageView.width
                                                height: bubble.implicitHeight
                                                Rectangle {
                                                    id: bubble
                                                    anchors.right: role === "user" ? parent.right : undefined
                                                    anchors.left: role === "assistant" ? parent.left : undefined
                                                    width: Math.min(parent.width * 0.72, Math.max(320, textBlock.paintedWidth + 44))
                                                    implicitHeight: bodyColumn.implicitHeight + 24
                                                    radius: 24
                                                    color: role === "user" ? "#191919" : "#131313"
                                                    border.color: role === "user" ? "#2b2b2b" : "#222222"
                                                    Column {
                                                        id: bodyColumn
                                                        anchors.fill: parent
                                                        anchors.margins: 14
                                                        spacing: 8
                                                        Text { text: author; color: role === "user" ? "#ceced3" : "#9c9ca2"; font.pixelSize: 11; font.weight: Font.Medium }
                                                        Text { id: textBlock; width: bubble.width - 28; text: content; wrapMode: Text.Wrap; color: "#f4f4f6"; font.pixelSize: 14; lineHeight: 1.18 }
                                                    }
                                                }
                                            }
                                        }
                                    }

                                    Rectangle {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 90
                                        radius: 26
                                        color: "#111111"
                                        border.color: "#1f1f1f"
                                        RowLayout {
                                            anchors.fill: parent
                                            anchors.margins: 14
                                            spacing: 10
                                            Button {
                                                id: plusButton
                                                Layout.preferredWidth: 48
                                                Layout.preferredHeight: 48
                                                onClicked: actionMenu.popup()
                                                background: Rectangle { radius: 16; color: "#171717"; border.color: "#2a2a2a" }
                                                contentItem: Text { text: "+"; color: "#f4f4f4"; font.pixelSize: 22; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                                            }
                                            TextArea {
                                                id: composer
                                                Layout.fillWidth: true
                                                Layout.fillHeight: true
                                                color: "#f5f5f5"
                                                placeholderText: "Message Luna..."
                                                placeholderTextColor: "#67676d"
                                                wrapMode: TextEdit.Wrap
                                                selectByMouse: true
                                                background: null
                                            }
                                            Button {
                                                Layout.preferredWidth: 48
                                                Layout.preferredHeight: 48
                                                onClicked: lunaBridge.noteAction("Microphone input is ready in the desktop voice layer.")
                                                background: Rectangle { radius: 16; color: "#171717"; border.color: "#2a2a2a" }
                                                contentItem: Text { text: "Mic"; color: "#f0f0f0"; font.pixelSize: 11; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                                            }
                                            Button {
                                                Layout.preferredWidth: 58
                                                Layout.preferredHeight: 48
                                                onClicked: lunaBridge.noteAction("Voice mode shell is ready for the next loop upgrade.")
                                                background: Rectangle { radius: 16; color: "#171717"; border.color: "#2a2a2a" }
                                                contentItem: Text { text: "Voice"; color: "#f0f0f0"; font.pixelSize: 11; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                                            }
                                            Button {
                                                Layout.preferredWidth: 104
                                                Layout.preferredHeight: 48
                                                onClicked: { lunaBridge.sendMessage(composer.text); composer.text = "" }
                                                background: Rectangle { radius: 18; color: "#f4f4f4" }
                                                contentItem: Text { text: "Send"; color: "#111111"; font.pixelSize: 14; font.weight: Font.DemiBold; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                                            }
                                        }
                                    }
                                }
                            }

                            Item {
                                RowLayout {
                                    anchors.fill: parent
                                    spacing: 16
                                    Rectangle {
                                        Layout.preferredWidth: 360
                                        Layout.fillHeight: true
                                        radius: 28
                                        color: "#101010"
                                        border.color: "#1e1e1e"
                                        ColumnLayout {
                                            anchors.fill: parent
                                            anchors.margins: 18
                                            spacing: 12
                                            Text { text: "Generated media"; color: "#f5f5f5"; font.pixelSize: 20; font.weight: Font.DemiBold }
                                            Text { text: "Black-and-white gallery for image and video outputs."; color: "#818188"; font.pixelSize: 12; wrapMode: Text.WordWrap }
                                            ListView {
                                                id: galleryList
                                                Layout.fillWidth: true
                                                Layout.fillHeight: true
                                                model: lunaBridge.galleryModel
                                                clip: true
                                                spacing: 8
                                                delegate: Rectangle {
                                                    required property string name
                                                    required property string meta
                                                    width: galleryList.width
                                                    height: 58
                                                    radius: 18
                                                    color: "#141414"
                                                    border.color: "#232323"
                                                    Column {
                                                        anchors.left: parent.left
                                                        anchors.leftMargin: 14
                                                        anchors.verticalCenter: parent.verticalCenter
                                                        spacing: 3
                                                        Text { text: name; color: "#f4f4f4"; font.pixelSize: 13 }
                                                        Text { text: meta; color: "#85858a"; font.pixelSize: 11 }
                                                    }
                                                    MouseArea { anchors.fill: parent; onClicked: lunaBridge.selectGalleryItem(index) }
                                                }
                                            }
                                        }
                                    }

                                    Rectangle {
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true
                                        radius: 28
                                        color: "#0f0f0f"
                                        border.color: "#1d1d1d"
                                        ColumnLayout {
                                            anchors.fill: parent
                                            anchors.margins: 22
                                            spacing: 14
                                            Text { text: lunaBridge.galleryPreviewTitle; color: "#fafafa"; font.pixelSize: 24; font.weight: Font.DemiBold }
                                            Text { text: lunaBridge.galleryPreviewMeta; color: "#8c8c92"; font.pixelSize: 12 }
                                            Rectangle {
                                                Layout.fillWidth: true
                                                Layout.fillHeight: true
                                                radius: 28
                                                color: "#121212"
                                                border.color: "#222222"
                                                clip: true
                                                Image {
                                                    anchors.fill: parent
                                                    anchors.margins: 18
                                                    source: lunaBridge.galleryPreviewPath
                                                    fillMode: Image.PreserveAspectFit
                                                    visible: lunaBridge.galleryPreviewPath !== "" && lunaBridge.galleryPreviewMeta.indexOf("Image") >= 0
                                                }
                                                Column {
                                                    anchors.centerIn: parent
                                                    spacing: 8
                                                    visible: !(lunaBridge.galleryPreviewPath !== "" && lunaBridge.galleryPreviewMeta.indexOf("Image") >= 0)
                                                    Text { text: "AI Media Surface"; color: "#f5f5f5"; font.pixelSize: 22; horizontalAlignment: Text.AlignHCenter }
                                                    Text { text: "Select an image or video from the gallery list."; color: "#8c8c92"; font.pixelSize: 12; horizontalAlignment: Text.AlignHCenter }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                            Item {
                                RowLayout {
                                    anchors.fill: parent
                                    spacing: 16
                                    Rectangle {
                                        Layout.preferredWidth: 340
                                        Layout.fillHeight: true
                                        radius: 28
                                        color: "#101010"
                                        border.color: "#1d1d1d"
                                        ColumnLayout {
                                            anchors.fill: parent
                                            anchors.margins: 18
                                            spacing: 12
                                            Text { text: "Projects"; color: "#f5f5f5"; font.pixelSize: 20; font.weight: Font.DemiBold }
                                            RowLayout {
                                                Layout.fillWidth: true
                                                spacing: 10
                                                TextField { id: projectNameField; Layout.fillWidth: true; placeholderText: "Project name"; color: "#f5f5f5"; placeholderTextColor: "#6d6d73"; background: Rectangle { radius: 16; color: "#141414"; border.color: "#232323" } }
                                                Button { text: "Create"; onClicked: lunaBridge.createProject(projectNameField.text, projectBrief.text) }
                                            }
                                            ListView {
                                                id: projectListView
                                                Layout.fillWidth: true
                                                Layout.fillHeight: true
                                                model: lunaBridge.projectsModel
                                                clip: true
                                                spacing: 8
                                                delegate: Rectangle {
                                                    required property string projectId
                                                    required property string name
                                                    required property string currentPhase
                                                    required property string taskCount
                                                    width: projectListView.width
                                                    height: 64
                                                    radius: 18
                                                    color: lunaBridge.currentProjectTitle === name ? "#171717" : "#131313"
                                                    border.color: lunaBridge.currentProjectTitle === name ? "#2f2f2f" : "#212121"
                                                    Column {
                                                        anchors.left: parent.left
                                                        anchors.leftMargin: 14
                                                        anchors.verticalCenter: parent.verticalCenter
                                                        spacing: 3
                                                        Text { text: name; color: "#f4f4f4"; font.pixelSize: 13; font.weight: Font.DemiBold }
                                                        Text { text: currentPhase + " - " + taskCount + " tasks"; color: "#8a8a90"; font.pixelSize: 11 }
                                                    }
                                                    MouseArea { anchors.fill: parent; onClicked: lunaBridge.selectProject(projectId) }
                                                }
                                            }
                                        }
                                    }

                                    Rectangle {
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true
                                        radius: 28
                                        color: "#0f0f0f"
                                        border.color: "#1d1d1d"
                                        ColumnLayout {
                                            anchors.fill: parent
                                            anchors.margins: 18
                                            spacing: 12
                                            RowLayout {
                                                Layout.fillWidth: true
                                                Text { text: lunaBridge.currentProjectTitle; color: "#fafafa"; font.pixelSize: 24; font.weight: Font.DemiBold }
                                                Item { Layout.fillWidth: true }
                                                Button { text: "Blueprint"; onClicked: lunaBridge.generateBlueprint(projectBrief.text) }
                                                Button { text: "Next step"; onClicked: lunaBridge.runNextStep() }
                                                Button { text: "Next chain"; onClicked: lunaBridge.runNextChain() }
                                            }
                                            Text { text: lunaBridge.currentProjectPhase + " - " + lunaBridge.currentProjectNextStep; color: "#85858b"; font.pixelSize: 12; wrapMode: Text.WordWrap }
                                            TextArea {
                                                id: projectBrief
                                                Layout.fillWidth: true
                                                Layout.preferredHeight: 120
                                                text: lunaBridge.currentProjectBrief()
                                                color: "#f5f5f5"
                                                placeholderText: "Write the project brief here..."
                                                placeholderTextColor: "#6d6d73"
                                                wrapMode: TextEdit.Wrap
                                                background: Rectangle { radius: 20; color: "#131313"; border.color: "#232323" }
                                            }
                                            RowLayout {
                                                Layout.fillWidth: true
                                                Layout.fillHeight: true
                                                spacing: 16
                                                Rectangle {
                                                    Layout.fillWidth: true
                                                    Layout.fillHeight: true
                                                    radius: 22
                                                    color: "#111111"
                                                    border.color: "#202020"
                                                    ColumnLayout {
                                                        anchors.fill: parent
                                                        anchors.margins: 16
                                                        spacing: 10
                                                        Text { text: "Task Center"; color: "#f5f5f5"; font.pixelSize: 18; font.weight: Font.DemiBold }
                                                        ListView {
                                                            id: taskListView
                                                            Layout.fillWidth: true
                                                            Layout.fillHeight: true
                                                            model: lunaBridge.tasksModel
                                                            clip: true
                                                            spacing: 8
                                                            delegate: Rectangle {
                                                                required property string title
                                                                required property string status
                                                                required property string tool
                                                                width: taskListView.width
                                                                height: 64
                                                                radius: 18
                                                                color: "#151515"
                                                                border.color: "#252525"
                                                                Column {
                                                                    anchors.left: parent.left
                                                                    anchors.leftMargin: 14
                                                                    anchors.verticalCenter: parent.verticalCenter
                                                                    spacing: 4
                                                                    Text { text: title; color: "#f4f4f4"; font.pixelSize: 13 }
                                                                    Text { text: status + " - " + tool; color: "#86868b"; font.pixelSize: 11 }
                                                                }
                                                                MouseArea { anchors.fill: parent; onClicked: lunaBridge.selectTask(index) }
                                                            }
                                                        }
                                                    }
                                                }
                                                Rectangle {
                                                    Layout.fillWidth: true
                                                    Layout.fillHeight: true
                                                    radius: 22
                                                    color: "#111111"
                                                    border.color: "#202020"
                                                    ColumnLayout {
                                                        anchors.fill: parent
                                                        anchors.margins: 16
                                                        spacing: 10
                                                        Text { text: "Task Detail"; color: "#f5f5f5"; font.pixelSize: 18; font.weight: Font.DemiBold }
                                                        ScrollView {
                                                            Layout.fillWidth: true
                                                            Layout.fillHeight: true
                                                            clip: true
                                                            Text { width: parent.width - 18; text: lunaBridge.taskDetailText + "\n\n" + lunaBridge.projectMemoryText; color: "#d2d2d7"; wrapMode: Text.Wrap; font.pixelSize: 12 }
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }

                            Item {
                                ColumnLayout {
                                    anchors.fill: parent
                                    spacing: 14
                                    Text { text: "Connected desktop integrations"; color: "#f5f5f5"; font.pixelSize: 24; font.weight: Font.DemiBold }
                                    Text { text: "Launch real connected tools without cluttering the visible AI surface."; color: "#85858b"; font.pixelSize: 12 }
                                    GridLayout {
                                        columns: 2
                                        rowSpacing: 14
                                        columnSpacing: 14
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true
                                        Repeater {
                                            model: lunaBridge.appsModel
                                            delegate: Rectangle {
                                                required property string key
                                                required property string label
                                                required property string path
                                                required property bool connected
                                                Layout.fillWidth: true
                                                Layout.fillHeight: true
                                                Layout.minimumHeight: 118
                                                radius: 24
                                                color: "#101010"
                                                border.color: connected ? "#2f2f2f" : "#1e1e1e"
                                                ColumnLayout {
                                                    anchors.fill: parent
                                                    anchors.margins: 18
                                                    spacing: 8
                                                    RowLayout {
                                                        Layout.fillWidth: true
                                                        Text { text: label; color: "#f5f5f5"; font.pixelSize: 18; font.weight: Font.DemiBold }
                                                        Item { Layout.fillWidth: true }
                                                        Rectangle {
                                                            radius: 12
                                                            color: connected ? "#f4f4f4" : "#1a1a1a"
                                                            border.color: connected ? "#f4f4f4" : "#2a2a2a"
                                                            implicitWidth: 76
                                                            implicitHeight: 26
                                                            Text { anchors.centerIn: parent; text: connected ? "Ready" : "Missing"; color: connected ? "#111111" : "#8a8a90"; font.pixelSize: 11 }
                                                        }
                                                    }
                                                    Text { text: path && path.length > 0 ? path : "No local path configured yet."; color: "#84848a"; font.pixelSize: 11; wrapMode: Text.WordWrap }
                                                    Item { Layout.fillHeight: true }
                                                    Button { text: "Open"; enabled: connected; onClicked: lunaBridge.launchConnectedApp(key) }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                            Item {
                                ColumnLayout {
                                    anchors.fill: parent
                                    spacing: 14
                                    Text { text: "System updates"; color: "#f5f5f5"; font.pixelSize: 24; font.weight: Font.DemiBold }
                                    Text { text: "Patch-note style system feed for Luna, Xeno, agent execution, and desktop actions."; color: "#85858b"; font.pixelSize: 12 }
                                    ListView {
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true
                                        model: lunaBridge.updatesModel
                                        clip: true
                                        spacing: 12
                                        delegate: Rectangle {
                                            required property string title
                                            required property string detail
                                            required property string status
                                            width: parent.width
                                            height: 94
                                            radius: 24
                                            color: "#101010"
                                            border.color: "#1e1e1e"
                                            RowLayout {
                                                anchors.fill: parent
                                                anchors.margins: 18
                                                spacing: 14
                                                Rectangle {
                                                    Layout.preferredWidth: 56
                                                    Layout.preferredHeight: 56
                                                    radius: 18
                                                    color: "#151515"
                                                    border.color: "#272727"
                                                    Text { anchors.centerIn: parent; text: status; color: "#f4f4f4"; font.pixelSize: 11 }
                                                }
                                                ColumnLayout {
                                                    Layout.fillWidth: true
                                                    spacing: 4
                                                    Text { text: title; color: "#f5f5f5"; font.pixelSize: 16; font.weight: Font.DemiBold }
                                                    Text { text: detail; color: "#8a8a90"; font.pixelSize: 12; wrapMode: Text.WordWrap }
                                                }
                                            }
                                        }
                                    }
                                }
                            }

                            Item {
                                ColumnLayout {
                                    anchors.fill: parent
                                    spacing: 14
                                    Text { text: "Friends / Groups"; color: "#f5f5f5"; font.pixelSize: 24; font.weight: Font.DemiBold }
                                    Text { text: "A calm systems view for the visible and hidden AI layers working together."; color: "#85858b"; font.pixelSize: 12 }
                                    Repeater {
                                        model: lunaBridge.friendsModel
                                        delegate: Rectangle {
                                            required property string name
                                            required property string status
                                            required property string detail
                                            Layout.fillWidth: true
                                            Layout.preferredHeight: 112
                                            radius: 26
                                            color: "#101010"
                                            border.color: "#1e1e1e"
                                            RowLayout {
                                                anchors.fill: parent
                                                anchors.margins: 18
                                                spacing: 16
                                                Rectangle {
                                                    Layout.preferredWidth: 72
                                                    Layout.preferredHeight: 72
                                                    radius: 24
                                                    color: "#141414"
                                                    border.color: "#262626"
                                                    Text { anchors.centerIn: parent; text: name.charAt(0); color: "#f5f5f5"; font.pixelSize: 24; font.weight: Font.DemiBold }
                                                }
                                                ColumnLayout {
                                                    Layout.fillWidth: true
                                                    spacing: 6
                                                    Text { text: name; color: "#f5f5f5"; font.pixelSize: 18; font.weight: Font.DemiBold }
                                                    Text { text: status; color: "#d1d1d6"; font.pixelSize: 12 }
                                                    Text { text: detail; color: "#8a8a90"; font.pixelSize: 12; wrapMode: Text.WordWrap }
                                                }
                                            }
                                        }
                                    }
                                }
                            }

                            Item {
                                ColumnLayout {
                                    anchors.fill: parent
                                    spacing: 14
                                    Text { text: "Settings / Control"; color: "#f5f5f5"; font.pixelSize: 24; font.weight: Font.DemiBold }
                                    Text { text: "Quiet control layer for permissions, trust, and runtime posture."; color: "#85858b"; font.pixelSize: 12 }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 14
                                        Repeater {
                                            model: lunaBridge.profilesModel
                                            delegate: Button {
                                                required property string key
                                                required property string label
                                                required property string description
                                                Layout.fillWidth: true
                                                Layout.preferredHeight: 110
                                                onClicked: lunaBridge.setControlProfile(key)
                                                background: Rectangle { radius: 24; color: "#101010"; border.color: "#1f1f1f" }
                                                contentItem: Column {
                                                    anchors.fill: parent
                                                    anchors.margins: 16
                                                    spacing: 8
                                                    Text { text: label; color: "#f5f5f5"; font.pixelSize: 18; font.weight: Font.DemiBold }
                                                    Text { text: description; color: "#8a8a90"; font.pixelSize: 12; wrapMode: Text.WordWrap }
                                                }
                                            }
                                        }
                                    }
                                    Rectangle {
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true
                                        radius: 28
                                        color: "#101010"
                                        border.color: "#1f1f1f"
                                        ScrollView {
                                            anchors.fill: parent
                                            anchors.margins: 18
                                            Text { width: parent.width - 18; text: lunaBridge.controlSummary; color: "#d2d2d7"; wrapMode: Text.Wrap; font.pixelSize: 13 }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    Menu {
        id: actionMenu
        MenuItem { text: "Add file"; onTriggered: lunaBridge.noteAction("File attachment action can be expanded in the execution layer.") }
        MenuItem { text: "Generate image"; onTriggered: lunaBridge.noteAction("Image generation flow will be routed through Luna and Gallery.") }
    }

    Menu {
        id: chatMenu
        MenuItem { text: "Rename"; onTriggered: { renameField.text = root.contextSessionTitle; renameDialog.open() } }
        MenuItem { text: "Pin chat"; onTriggered: lunaBridge.pinChat(root.contextSessionId) }
        MenuItem { text: "Delete"; onTriggered: lunaBridge.deleteChat(root.contextSessionId) }
        MenuItem { text: "Archive"; onTriggered: lunaBridge.archiveChat(root.contextSessionId) }
    }

    Dialog {
        id: renameDialog
        modal: true
        x: (root.width - width) / 2
        y: (root.height - height) / 2
        width: 380
        height: 190
        padding: 0
        background: Rectangle { radius: 24; color: "#101010"; border.color: "#232323" }
        contentItem: ColumnLayout {
            anchors.fill: parent
            anchors.margins: 18
            spacing: 14
            Text { text: "Rename chat"; color: "#f5f5f5"; font.pixelSize: 20; font.weight: Font.DemiBold }
            TextField { id: renameField; Layout.fillWidth: true; color: "#f5f5f5"; placeholderText: "Chat title"; placeholderTextColor: "#6d6d73"; background: Rectangle { radius: 16; color: "#151515"; border.color: "#252525" } }
            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                Button { text: "Cancel"; onClicked: renameDialog.close() }
                Button { text: "Save"; onClicked: { lunaBridge.renameChat(root.contextSessionId, renameField.text); renameDialog.close() } }
            }
        }
    }

    Popup {
        id: profilePopup
        modal: false
        x: root.width - width - 34
        y: 86
        width: 320
        height: 280
        padding: 0
        background: Rectangle { radius: 28; color: "#101010"; border.color: "#232323" }
        contentItem: ColumnLayout {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 12
            RowLayout {
                spacing: 12
                Rectangle {
                    Layout.preferredWidth: 54
                    Layout.preferredHeight: 54
                    radius: 27
                    color: "#171717"
                    border.color: "#2a2a2a"
                    clip: true
                    Image { anchors.fill: parent; source: lunaBridge.profileImagePath; fillMode: Image.PreserveAspectCrop; visible: source !== "" }
                    Text { anchors.centerIn: parent; visible: lunaBridge.profileImagePath === ""; text: lunaBridge.profileName.length > 0 ? lunaBridge.profileName.charAt(0).toUpperCase() : "L"; color: "#f5f5f5"; font.pixelSize: 20; font.weight: Font.DemiBold }
                }
                ColumnLayout {
                    spacing: 2
                    Text { text: lunaBridge.profileName; color: "#f5f5f5"; font.pixelSize: 18; font.weight: Font.DemiBold }
                    Text { text: "Identity / Device layer"; color: "#8a8a90"; font.pixelSize: 11 }
                }
            }
            Rectangle { Layout.fillWidth: true; height: 1; color: "#202020" }
            Text { text: "Device"; color: "#f5f5f5"; font.pixelSize: 14; font.weight: Font.DemiBold }
            Text { text: lunaBridge.deviceInfo; color: "#8a8a90"; font.pixelSize: 12; wrapMode: Text.WordWrap }
            Text { text: "Version"; color: "#f5f5f5"; font.pixelSize: 14; font.weight: Font.DemiBold }
            Text { text: lunaBridge.appVersion; color: "#8a8a90"; font.pixelSize: 12 }
            Item { Layout.fillHeight: true }
            Button { text: "Close"; Layout.alignment: Qt.AlignRight; onClicked: profilePopup.close() }
        }
    }
}
