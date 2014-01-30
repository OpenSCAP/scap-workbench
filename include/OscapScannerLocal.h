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

#ifndef SCAP_WORKBENCH_OSCAP_SCANNER_LOCAL_H_
#define SCAP_WORKBENCH_OSCAP_SCANNER_LOCAL_H_

#include "ForwardDecls.h"
#include "OscapScannerBase.h"

class OscapScannerLocal : public OscapScannerBase
{
    Q_OBJECT

    public:
        OscapScannerLocal();
        virtual ~OscapScannerLocal();

        virtual void evaluate();

    private:
        static QString getPkexecOscapPath();

};

#endif
