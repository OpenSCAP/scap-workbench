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

#ifndef SCAP_WORKBENCH_TAILORING_UNDO_COMMANDS_H_
#define SCAP_WORKBENCH_TAILORING_UNDO_COMMANDS_H_

#include "ForwardDecls.h"

#include <QUndoCommand>
#include <QTreeWidgetItem>

extern "C"
{
#include <xccdf_benchmark.h>
#include <xccdf_policy.h>
}

/**
 * @brief Stores info about one selection or deselection of an XCCDF item
 */
class XCCDFItemSelectUndoCommand : public QUndoCommand
{
    public:
        XCCDFItemSelectUndoCommand(TailoringWindow* window, QTreeWidgetItem* item, bool newSelect);
        virtual ~XCCDFItemSelectUndoCommand();

        virtual int id() const;

        virtual void redo();
        virtual void undo();

    private:
        void refreshText();

        TailoringWindow* mWindow;

        QTreeWidgetItem* mTreeItem;
        /// selection state after this undo command is "redone" (applied)
        bool mNewSelect;
};

/**
 * @brief Stores info about refinement of xccdf:Value's value
 */
class XCCDFValueChangeUndoCommand : public QUndoCommand
{
    public:
        XCCDFValueChangeUndoCommand(TailoringWindow* window, struct xccdf_value* xccdfValue, const QString& newValue, const QString& oldValue);
        virtual ~XCCDFValueChangeUndoCommand();

        virtual int id() const;

        virtual bool mergeWith(const QUndoCommand* other);

        virtual void redo();
        virtual void undo();

    private:
        void refreshText();

        TailoringWindow* mWindow;

        struct xccdf_value* mXccdfValue;
        /// value after this undo command is "redone" (applied)
        QString mNewValue;
        /// value after this undo command is "undone"
        QString mOldValue;
};

/**
 * @brief Stores XCCDF profile title change undo info
 */
class ProfileTitleChangeUndoCommand : public QUndoCommand
{
    public:
        ProfileTitleChangeUndoCommand(TailoringWindow* window, const QString& oldTitle, const QString& newTitle);
        virtual ~ProfileTitleChangeUndoCommand();

        virtual int id() const;

        virtual void redo();
        virtual void undo();

        virtual bool mergeWith(const QUndoCommand *other);

    private:
        void refreshText();

        TailoringWindow* mWindow;

        QString mOldTitle;
        QString mNewTitle;
};

/**
 * @brief Stores XCCDF profile description change undo info
 */
class ProfileDescriptionChangeUndoCommand : public QUndoCommand
{
    public:
        ProfileDescriptionChangeUndoCommand(TailoringWindow* window, const QString& oldDesc, const QString& newDesc);
        virtual ~ProfileDescriptionChangeUndoCommand();

        virtual int id() const;

        virtual void redo();
        virtual void undo();

        virtual bool mergeWith(const QUndoCommand *other);

    private:
        void refreshText();

        TailoringWindow* mWindow;

        QString mOldDesc;
        QString mNewDesc;
};

#endif
