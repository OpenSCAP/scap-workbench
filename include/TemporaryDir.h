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

#ifndef SCAP_WORKBENCH_TEMPORARY_DIR_H_
#define SCAP_WORKBENCH_TEMPORARY_DIR_H_

#include "ForwardDecls.h"
#include <QString>

/**
 * @brief Creates a (LOCAL!) temporary directory and auto destroys it if told so
 *
 * This structure is lazy, it only creates the temp directory when asked about
 * its path. Before you query the path the directory won't be created.
 *
 * @note Default setting is to auto-remove the directory on destruction.
 * @internal We should replace this with QTemporaryDir when scap-workbench moves to Qt5
 */
class TemporaryDir
{
    public:
        TemporaryDir();
        ~TemporaryDir();

        /**
         * @brief Changes the auto-remove settings
         *
         * If autoRemove is true the structure will recursively remove the entire
         * temporary directory (that is the default setting). Else it will just
         * create it and it's up to the user to destroy it.
         */
        void setAutoRemove(const bool autoRemove);

        /// @see TemporaryDir::setAutoRemove
        bool getAutoRemove() const;

        /**
         * @brief Returns absolute path of created temporary directory
         *
         * @exception TemporaryDirException Failed to create temporary directory (nonzero exit code from mktemp -d)
         */
        const QString& getPath() const;

    private:
        /**
         * Ensures that temporary directory has been created and the stored path is valid.
         */
        void ensurePath() const;

        /// Holds absolute path of the created temporary directory
        mutable QString mPath;
        /// @see TemporaryDir::setAutoRemove
        bool mAutoRemove;
};

#endif
