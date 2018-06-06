/*
 * Copyright 2013 Red Hat Inc., Durham, North Carolina.
 * All Rights Reserved.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * Authors:
 *      Martin Preisler <mpreisle@redhat.com>
 */

#include "TailoringUndoCommands.h"
#include "TailoringWindow.h"

ProfileTitleChangeUndoCommand::ProfileTitleChangeUndoCommand(TailoringWindow* window, const QString& oldTitle, const QString& newTitle):
    mWindow(window),
    mOldTitle(oldTitle),
    mNewTitle(newTitle)
{
    refreshText();
}

ProfileTitleChangeUndoCommand::~ProfileTitleChangeUndoCommand()
{}

int ProfileTitleChangeUndoCommand::id() const
{
    return 2;
}

void ProfileTitleChangeUndoCommand::redo()
{
    mWindow->setProfileTitle(mNewTitle);
    mWindow->refreshProfileDockWidget();
}

void ProfileTitleChangeUndoCommand::undo()
{
    mWindow->setProfileTitle(mOldTitle);
    mWindow->refreshProfileDockWidget();
}

bool ProfileTitleChangeUndoCommand::mergeWith(const QUndoCommand *other)
{
    if (other->id() != id())
        return false;

    mNewTitle = static_cast<const ProfileTitleChangeUndoCommand*>(other)->mNewTitle;
    refreshText();
    return true;
}

void ProfileTitleChangeUndoCommand::refreshText()
{
    setText(QObject::tr("profile title to \"%1\"").arg(mNewTitle));
}

ProfileDescriptionChangeUndoCommand::ProfileDescriptionChangeUndoCommand(TailoringWindow* window, const QString& oldDesc, const QString& newDesc):
    mWindow(window),
    mOldDesc(oldDesc),
    mNewDesc(newDesc)
{
    refreshText();
}

ProfileDescriptionChangeUndoCommand::~ProfileDescriptionChangeUndoCommand()
{}

int ProfileDescriptionChangeUndoCommand::id() const
{
    return 3;
}

void ProfileDescriptionChangeUndoCommand::redo()
{
    mWindow->setProfileDescription(mNewDesc);
    mWindow->refreshProfileDockWidget();
}

void ProfileDescriptionChangeUndoCommand::undo()
{
    mWindow->setProfileDescription(mOldDesc);
    mWindow->refreshProfileDockWidget();
}

bool ProfileDescriptionChangeUndoCommand::mergeWith(const QUndoCommand *other)
{
    if (other->id() != id())
        return false;

    mNewDesc = static_cast<const ProfileDescriptionChangeUndoCommand*>(other)->mNewDesc;
    refreshText();
    return true;
}

void ProfileDescriptionChangeUndoCommand::refreshText()
{
    QString shortDesc = mNewDesc;
    shortDesc.truncate(32);
    shortDesc += "...";

    setText(QObject::tr("profile description to \"%1\"").arg(shortDesc));
}

XCCDFItemSelectUndoCommand::XCCDFItemSelectUndoCommand(TailoringWindow* window, QTreeWidgetItem* item, bool newSelect):
    mWindow(window),
    mTreeItem(item),
    mNewSelect(newSelect)
{
    refreshText();
}

XCCDFItemSelectUndoCommand::~XCCDFItemSelectUndoCommand()
{}

int XCCDFItemSelectUndoCommand::id() const
{
    return 1;
}

void XCCDFItemSelectUndoCommand::redo()
{
    struct xccdf_item* xccdfItem = TailoringWindow::getXccdfItemFromTreeItem(mTreeItem);
    mWindow->setItemSelected(xccdfItem, mNewSelect);
}

void XCCDFItemSelectUndoCommand::undo()
{
    struct xccdf_item* xccdfItem = TailoringWindow::getXccdfItemFromTreeItem(mTreeItem);
    mWindow->setItemSelected(xccdfItem, !mNewSelect);
}

void XCCDFItemSelectUndoCommand::refreshText()
{
    struct xccdf_item* xccdfItem = TailoringWindow::getXccdfItemFromTreeItem(mTreeItem);
    QString title = mWindow->getXCCDFItemTitle(xccdfItem);
    if (title.isEmpty())
        title = QString::fromUtf8(xccdf_item_get_id(xccdfItem));

    if (mNewSelect)
        setText(QObject::tr("Select Rule \"%1\"").arg(title));
    else
        setText(QObject::tr("Deselect Rule \"%1\"").arg(title));
}

XCCDFValueChangeUndoCommand::XCCDFValueChangeUndoCommand(TailoringWindow* window, struct xccdf_value* xccdfValue, const QString& newValue, const QString& oldValue):
    mWindow(window),
    mXccdfValue(xccdfValue),

    mNewValue(newValue),
    mOldValue(oldValue)
{
    refreshText();
}

XCCDFValueChangeUndoCommand::~XCCDFValueChangeUndoCommand()
{}

int XCCDFValueChangeUndoCommand::id() const
{
    return 4;
}

bool XCCDFValueChangeUndoCommand::mergeWith(const QUndoCommand* other)
{
    if (other->id() != id())
        return false;

    const XCCDFValueChangeUndoCommand* command = static_cast<const XCCDFValueChangeUndoCommand*>(other);

    if (command->mXccdfValue != mXccdfValue)
        return false;

    mNewValue = command->mNewValue;
    refreshText();
    return true;
}

void XCCDFValueChangeUndoCommand::redo()
{
    mWindow->setValueValue(mXccdfValue, mNewValue);
    mWindow->refreshXccdfItemPropertiesDockWidget();
}

void XCCDFValueChangeUndoCommand::undo()
{
    mWindow->setValueValue(mXccdfValue, mOldValue);
    mWindow->refreshXccdfItemPropertiesDockWidget();
}

void XCCDFValueChangeUndoCommand::refreshText()
{
    QString title = mWindow->getXCCDFItemTitle(xccdf_value_to_item(mXccdfValue));
    if (title.isEmpty())
        title = QString::fromUtf8(xccdf_value_get_id(mXccdfValue));

    setText(QObject::tr("Set Value '%1' to '%2'").arg(title, mNewValue));
}
